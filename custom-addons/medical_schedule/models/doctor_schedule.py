# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.resource.models.resource import Intervals
from odoo.tools import timezone as odoo_timezone_util # Corrected import alias
import pytz
from datetime import datetime, time, timedelta # Added datetime, time

class DoctorSchedule(models.Model):
    _name = 'medical.doctor.schedule'
    _description = 'Doctor Working Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    doctor_id = fields.Many2one(
        'res.partner',
        string='Doctor',
        required=True,
        domain="[('is_doctor', '=', True)]",
        help="The doctor for whom this schedule is defined."
    )
    name = fields.Char(compute='_compute_name', store=True, readonly=True)
    date_from = fields.Date(string='Date From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Date To') # Optional: for schedules that have an end date

    # Using resource.calendar.attendance model for defining working hours
    # This leverages Odoo's existing working time definitions.
    attendance_ids = fields.One2many(
        'resource.calendar.attendance',
        'doctor_schedule_id', # New field to link back to this model
        string='Working Hours',
        copy=True
    )

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('doctor_date_uniq', 'unique(doctor_id, date_from, company_id)', 'A doctor can only have one schedule starting from a specific date for the same company.')
    ]

    @api.depends('doctor_id', 'date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            name = f"Schedule for {record.doctor_id.name or 'N/A'}"
            if record.date_from:
                name += f" from {record.date_from.strftime('%Y-%m-%d')}"
            if record.date_to:
                name += f" to {record.date_to.strftime('%Y-%m-%d')}"
            record.name = name

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError(_("The 'Date From' cannot be later than the 'Date To'."))

    def _get_combined_schedule_intervals(self, doctor_id_obj, start_dt_utc, end_dt_utc, doctor_tz_str):
        """
        Calculates the available UTC time intervals for a doctor within a given UTC datetime range.
        This method considers the doctor's general schedules (converting daily hours from doctor's timezone to UTC)
        and their specific UTC-defined exceptions (like holidays or time off).

        :param doctor_id_obj: res.partner record of the doctor.
        :param start_dt_utc: datetime object in UTC, representing the start of the period to check.
        :param end_dt_utc: datetime object in UTC, representing the end of the period to check.
        :param doctor_tz_str: string, the doctor's timezone (e.g., 'America/New_York').
        :return: Intervals object (list of tuples [(start_utc, end_utc, record_id)]) representing available slots.
        """
        # This method is defined on medical.doctor.schedule.
        # It should be called on the specific schedule record relevant for the doctor and date.
        # If a doctor has multiple schedules (e.g. main and a temporary one), logic to select/combine them
        # would be needed here or before calling this. For now, assumes 'self' is the one to use.
        # If called from a context where 'self' is not a schedule (e.g. directly from appointment model),
        # it would first need to find the relevant schedule(s).

        if not doctor_id_obj or not self.active: # Ensure the schedule itself is active
            return Intervals([])

        doctor_tz = pytz.timezone(doctor_tz_str or 'UTC') # Default to UTC if no tz provided
        utc_tz = pytz.utc

        # 1. Calculate base working intervals from this specific schedule in UTC
        working_intervals_utc = Intervals([])

        # Effective start and end for this schedule's applicability to the query range
        schedule_eff_start_date = self.date_from
        schedule_eff_end_date = self.date_to or (end_dt_utc.date() + timedelta(days=1)) # Open-ended if no date_to

        # Iterate day by day within the intersection of:
        # a) The query range [start_dt_utc.date(), end_dt_utc.date()]
        # b) This schedule's active range [schedule_eff_start_date, schedule_eff_end_date]

        loop_date = max(start_dt_utc.date(), schedule_eff_start_date)
        final_loop_date = min(end_dt_utc.date(), schedule_eff_end_date) # Corrected this line

        while loop_date <= final_loop_date:
            # Skip if loop_date is outside schedule's own date_from/date_to
            if self.date_from and loop_date < self.date_from:
                loop_date += timedelta(days=1)
                continue
            if self.date_to and loop_date > self.date_to:
                break # Past schedule's validity

            weekday_str = str(loop_date.weekday()) # Odoo's dayofweek: 0=Mon, 1=Tue ... 6=Sun

            for attendance in self.attendance_ids.filtered(
                lambda att: att.dayofweek == weekday_str and
                (not att.date_from or att.date_from <= loop_date) and # Attendance line valid for this day
                (not att.date_to or att.date_to >= loop_date)       # Attendance line valid for this day
            ):
                naive_from_dt = datetime.combine(loop_date, time(0, 0)) + timedelta(hours=attendance.hour_from)
                naive_to_dt = datetime.combine(loop_date, time(0, 0)) + timedelta(hours=attendance.hour_to)

                local_from_dt = doctor_tz.localize(naive_from_dt, is_dst=None)
                local_to_dt = doctor_tz.localize(naive_to_dt, is_dst=None)

                utc_from_dt_for_day = local_from_dt.astimezone(utc_tz)
                utc_to_dt_for_day = local_to_dt.astimezone(utc_tz)

                # Intersect with the overall query range [start_dt_utc, end_dt_utc]
                interval_start = max(utc_from_dt_for_day, start_dt_utc)
                interval_end = min(utc_to_dt_for_day, end_dt_utc)

                if interval_start < interval_end:
                    # Using self (the schedule record) as the meta-information for the interval
                    working_intervals_utc = working_intervals_utc | Intervals([(interval_start, interval_end, self)])
            loop_date += timedelta(days=1)

        # 2. Fetch and prepare UTC exceptions for the doctor for THIS schedule's company
        # This assumes exceptions are global for a doctor in a company, not per-schedule.
        # If exceptions could be per-schedule, the model for exceptions would need a link to medical.doctor.schedule.
        exception_intervals_utc = Intervals([])
        exceptions_domain = [
            ('doctor_id', '=', doctor_id_obj.id),
            ('active', '=', True),
            ('date_from', '<', end_dt_utc),
            ('date_to', '>', start_dt_utc),
        ]
        if self.company_id: # Filter exceptions by the schedule's company if set
            exceptions_domain.append(('company_id', '=', self.company_id.id))

        exceptions = self.env['medical.doctor.schedule.exception'].search(exceptions_domain)

        for exc in exceptions:
            exc_start_utc = exc.date_from # Assumed to be UTC
            exc_end_utc = exc.date_to     # Assumed to be UTC

            clamped_exc_start = max(exc_start_utc, start_dt_utc)
            clamped_exc_end = min(exc_end_utc, end_dt_utc)

            if clamped_exc_start < clamped_exc_end:
                 # Using the exception record as meta-information
                 exception_intervals_utc = exception_intervals_utc | Intervals([(clamped_exc_start, clamped_exc_end, exc)])

        # 3. Subtract exceptions from working intervals
        available_intervals_utc = working_intervals_utc - exception_intervals_utc

        return available_intervals_utc

class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    # Add a field to link attendances to a doctor's schedule
    # This is an alternative to creating a new model for schedule lines if
    # resource.calendar.attendance is sufficient.
    doctor_schedule_id = fields.Many2one('medical.doctor.schedule', string='Doctor Schedule', ondelete='cascade')
    # If we need more specific types of slots, we can add them here or in a related model
    # For example, 'appointment_type_id' or 'slot_capacity'

class DoctorScheduleException(models.Model):
    _name = 'medical.doctor.schedule.exception'
    _description = 'Doctor Schedule Exception (e.g., Holiday, Time Off)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, doctor_id'

    name = fields.Char(required=True, tracking=True)
    doctor_id = fields.Many2one(
        'res.partner',
        string='Doctor',
        required=True,
        domain="[('is_doctor', '=', True)]",
        help="The doctor for whom this exception applies."
    )
    date_from = fields.Datetime(string='From', required=True, tracking=True)
    date_to = fields.Datetime(string='To', required=True, tracking=True)
    reason = fields.Text(string='Reason')
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from >= record.date_to:
                raise ValidationError(_("'From' date must be earlier than 'To' date."))

            # Check for overlapping exceptions for the same doctor
            overlapping_exceptions = self.search([
                ('id', '!=', record.id),
                ('doctor_id', '=', record.doctor_id.id),
                ('date_from', '<', record.date_to),
                ('date_to', '>', record.date_from),
                ('company_id', '=', record.company_id.id)
            ])
            if overlapping_exceptions:
                raise ValidationError(_("This exception overlaps with another existing exception for the same doctor."))
