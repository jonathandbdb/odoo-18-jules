# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ # Added _
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.addons.resource.models.resource import Intervals # For Intervals type
from odoo.tools import timezone as odoo_timezone_util
import pytz # For timezone localization

class MedicalPatient(models.Model):
    _name = 'medical.patient'
    _inherit = 'res.partner' # Inheriting from res.partner
    _description = 'Medical Patient'

    # Add patient-specific fields here if needed in the future
    # For now, we leverage res.partner fields

class MedicalDoctor(models.Model):
    _name = 'medical.doctor'
    _inherit = 'res.partner' # Inheriting from res.partner
    _description = 'Medical Doctor'

    specialty_ids = fields.Many2many('medical.specialty', string='Specialties')
    # Add other doctor-specific fields here, e.g., employee ID if not using hr.employee

class MedicalSpecialty(models.Model):
    _name = 'medical.specialty'
    _description = 'Medical Specialty'

    name = fields.Char(string='Specialty Name', required=True)
    description = fields.Text(string='Description')

class MedicalAppointment(models.Model):
    _name = 'medical.appointment'
    _description = 'Medical Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # For communication and activities

    patient_id = fields.Many2one('medical.patient', string='Patient', required=True, domain="[('is_company', '=', False)]", help="Patient for this appointment")
    doctor_id = fields.Many2one('medical.doctor', string='Doctor', required=True, domain="[('is_company', '=', False)]", help="Doctor for this appointment")
    appointment_date = fields.Datetime(string='Appointment Date', required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', default=0.5) # Default 30 mins
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    notes = fields.Text(string='Notes')

    # Link to calendar event for Odoo calendar integration
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        appointments = super(MedicalAppointment, self).create(vals_list)
        for appointment in appointments:
            if not appointment.calendar_event_id:
                event_vals = appointment._prepare_calendar_event_values()
                calendar_event = self.env['calendar.event'].create(event_vals)
                appointment.calendar_event_id = calendar_event.id
        return appointments

    def write(self, vals):
        res = super(MedicalAppointment, self).write(vals)
        for appointment in self:
            if appointment.calendar_event_id:
                event_vals = appointment._prepare_calendar_event_values()
                # Exclude 'id' from event_vals if it's there to avoid trying to update it
                event_vals.pop('id', None)
                appointment.calendar_event_id.write(event_vals)
            elif 'appointment_date' in vals or 'doctor_id' in vals or 'patient_id' in vals: # Create if not exists and key fields change
                event_vals = appointment._prepare_calendar_event_values()
                calendar_event = self.env['calendar.event'].create(event_vals)
                appointment.calendar_event_id = calendar_event.id
        return res

    def unlink(self):
        self.mapped('calendar_event_id').unlink()
        return super(MedicalAppointment, self).unlink()

    def _prepare_calendar_event_values(self):
        self.ensure_one()
        return {
            'name': f"Appointment: {self.patient_id.name} with {self.doctor_id.name}",
            'start': self.appointment_date,
            'stop': fields.Datetime.add(self.appointment_date, hours=self.duration),
            'partner_ids': [(6, 0, [self.patient_id.id, self.doctor_id.id])], # Link patient and doctor
            'user_id': self.doctor_id.user_id.id if self.doctor_id.user_id else self.env.user.id, # Assign to doctor's user or current user
            'allday': False,
            'privacy': 'private',
            'res_id': self.id,
            'res_model': self._name,
            # You might want to add more fields like location, etc.
        }

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        # Additional logic for confirmation if needed

    def action_done(self):
        self.write({'state': 'done'})
        # Additional logic for completion if needed

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        if self.calendar_event_id:
            self.calendar_event_id.unlink() # Remove calendar event on cancellation
        # Additional logic for cancellation if needed

    def action_draft(self):
        self.write({'state': 'draft'})
        # Additional logic for setting to draft if needed

    @api.constrains('appointment_date', 'doctor_id', 'duration', 'state')
    def _check_doctor_availability(self):
        for appointment in self.filtered(lambda app: app.state not in ['cancelled', 'done'] and app.doctor_id and app.appointment_date):
            if not appointment.doctor_id or not appointment.appointment_date or not appointment.duration:
                # Not enough info to check, or not relevant for cancelled/done states
                continue

            appointment_start_utc = appointment.appointment_date # Already UTC as Odoo stores Datetime in UTC
            appointment_end_utc = appointment_start_utc + timedelta(hours=appointment.duration)

            # Doctor's timezone - assuming it's on the res.partner (doctor) record or a default
            # For Odoo Online, user.tz is often the user's preference, not necessarily the doctor's working TZ.
            # medical.doctor inherits res.partner, which has a 'tz' field.
            doctor_tz_str = appointment.doctor_id.tz or self.env.user.tz or 'UTC' # Fallback chain for TZ

            # Find the relevant schedule(s) for the doctor and appointment date
            # A doctor might have multiple schedule records (e.g., past, current, future).
            # We need the one that is active for the appointment_date.
            # If date_to is null on schedule, it means it's ongoing.
            schedules = self.env['medical.doctor.schedule'].search([
                ('doctor_id', '=', appointment.doctor_id.id),
                ('active', '=', True),
                ('date_from', '<=', appointment_start_utc.date()),
                '|',
                ('date_to', '>=', appointment_start_utc.date()),
                ('date_to', '=', False)
            ], order='date_from desc') # Prioritize schedules that start later if overlapping

            if not schedules:
                raise ValidationError(
                    _("Dr. %s does not have an active schedule covering %s. Please define a schedule first.") %
                    (appointment.doctor_id.name, fields.Date.to_string(appointment_start_utc.date()))
                )

            # For this example, we'll use the first relevant schedule found.
            # More complex logic might be needed if schedules can overlap or be combined.
            # The _get_combined_schedule_intervals is on the schedule record.
            relevant_schedule = schedules[0]

            # Query a slightly wider range to catch edge cases with TZ conversions for the day's attendances
            query_start_utc = appointment_start_utc - timedelta(days=1)
            query_end_utc = appointment_end_utc + timedelta(days=1)

            available_intervals_utc = relevant_schedule._get_combined_schedule_intervals(
                appointment.doctor_id,
                query_start_utc, # Check a wider range to be safe with TZ conversions
                query_end_utc,
                doctor_tz_str
            )

            # Check if the appointment interval [app_start, app_end] is contained in available_intervals_utc
            appointment_interval = Intervals([(appointment_start_utc, appointment_end_utc, self.env['medical.appointment'])])

            # Intersection of available slots and the desired appointment slot
            intersection_intervals = available_intervals_utc & appointment_interval

            if intersection_intervals != appointment_interval:
                # The desired slot is not fully available.
                # Try to provide some helpful feedback, e.g., list available slots on that day.
                user_tz_str = self.env.user.tz or 'UTC'
                user_tz = pytz.timezone(user_tz_str)

                # Get available slots for the specific day of the appointment in user's timezone
                day_start_user_tz = odoo_timezone_util.remove_ secretário_tzinfo(appointment_start_utc.astimezone(user_tz).replace(hour=0, minute=0, second=0, microsecond=0))
                day_end_user_tz = day_start_user_tz + timedelta(days=1)

                day_start_utc = user_tz.localize(day_start_user_tz).astimezone(pytz.utc)
                day_end_utc = user_tz.localize(day_end_user_tz).astimezone(pytz.utc)

                # Re-query available intervals for the specific day for better suggestions
                daily_available_utc = relevant_schedule._get_combined_schedule_intervals(
                    appointment.doctor_id, day_start_utc, day_end_utc, doctor_tz_str
                )

                suggestions = []
                for start_utc, end_utc, _meta in daily_available_utc:
                    start_user = start_utc.astimezone(user_tz)
                    end_user = end_utc.astimezone(user_tz)
                    suggestions.append(f"{start_user.strftime('%H:%M')} - {end_user.strftime('%H:%M')}")

                error_msg = _(
                    "The selected time for Dr. %s is not available.\n"
                    "Appointment: %s from %s to %s (UTC).\n"
                    "Please choose a different time."
                ) % (
                    appointment.doctor_id.name,
                    appointment.display_name,
                    appointment_start_utc.strftime('%Y-%m-%d %H:%M'),
                    appointment_end_utc.strftime('%Y-%m-%d %H:%M')
                )
                if suggestions:
                    error_msg += _("\nAvailable slots on %s (in %s timezone):\n%s") % (
                        appointment_start_utc.astimezone(user_tz).strftime('%Y-%m-%d'),
                        user_tz_str,
                        "\n".join(suggestions)
                    )
                else:
                    error_msg += _("\nThere are no available slots for Dr. %s on %s.") % (
                        appointment.doctor_id.name,
                        appointment_start_utc.astimezone(user_tz).strftime('%Y-%m-%d')
                    )
                raise ValidationError(error_msg)
