# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, time, date, timedelta
import pytz

class TestScheduleAvailability(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestScheduleAvailability, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Create a medical category and groups if they don't exist (similar to appointment tests)
        cls.medical_category = cls.env['ir.module.category'].search([('name', '=', 'Medical')], limit=1)
        if not cls.medical_category:
            cls.medical_category = cls.env['ir.module.category'].create({'name': 'Medical'})

        cls.group_medical_user = cls.env['res.groups'].search([('name', '=', 'Medical / User')], limit=1)
        if not cls.group_medical_user:
            cls.group_medical_user = cls.env['res.groups'].create({
                'name': 'Medical / User', 'category_id': cls.medical_category.id
            })

        # Create a Doctor
        cls.doctor_jones = cls.env['res.partner'].create({
            'name': 'Dr. Indiana Jones',
            'is_doctor': True,
            'tz': 'America/Denver', # Doctor's timezone
        })

        # Today's date for creating schedules
        cls.today = date.today()
        cls.tomorrow = cls.today + timedelta(days=1)

        # Doctor Jones's Schedule (e.g., Mon-Fri 9-12, 13-17 Denver Time)
        cls.schedule_jones = cls.env['medical.doctor.schedule'].create({
            'doctor_id': cls.doctor_jones.id,
            'date_from': cls.today.replace(month=1, day=1), # From beginning of year
            'date_to': False, # Ongoing
            'company_id': cls.env.company.id,
            'attendance_ids': [
                (0, 0, {'name': 'Weekday Morning', 'dayofweek': str(i), 'hour_from': 9.0, 'hour_to': 12.0})
                for i in range(5) # Monday to Friday
            ] + [
                (0, 0, {'name': 'Weekday Afternoon', 'dayofweek': str(i), 'hour_from': 13.0, 'hour_to': 17.0})
                for i in range(5) # Monday to Friday
            ]
        })

    def _get_utc_dt(self, date_obj, hour, minute, tz_str):
        """Helper to create a UTC datetime from date, H, M in a specific timezone."""
        local_tz = pytz.timezone(tz_str)
        naive_dt = datetime.combine(date_obj, time(hour, minute))
        local_dt = local_tz.localize(naive_dt)
        return local_dt.astimezone(pytz.utc)

    def test_01_doctor_available_working_hours(self):
        """Check availability during working hours."""
        # Find a Tuesday (dayofweek='1')
        test_date = self.today
        while test_date.weekday() != 1: # 1 is Tuesday
            test_date += timedelta(days=1)

        # 10:00 AM Denver time on that Tuesday
        start_dt_utc = self._get_utc_dt(test_date, 10, 0, self.doctor_jones.tz)
        end_dt_utc = self._get_utc_dt(test_date, 11, 0, self.doctor_jones.tz) # 1 hour duration

        available_intervals = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, start_dt_utc, end_dt_utc, self.doctor_jones.tz
        )

        # The interval should contain [start_dt_utc, end_dt_utc]
        # Format of intervals: list of [ (start, end, recordset) ]
        is_available = any(
            interval_start <= start_dt_utc and interval_end >= end_dt_utc
            for interval_start, interval_end, _ in available_intervals
        )
        self.assertTrue(is_available, "Doctor should be available at 10:00 AM on a working day.")

    def test_02_doctor_unavailable_outside_working_hours(self):
        """Check unavailability outside working hours (e.g., 8 AM)."""
        test_date = self.today
        while test_date.weekday() != 1: # Tuesday
            test_date += timedelta(days=1)

        # 8:00 AM Denver time (doctor starts at 9:00)
        start_dt_utc = self._get_utc_dt(test_date, 8, 0, self.doctor_jones.tz)
        end_dt_utc = self._get_utc_dt(test_date, 9, 0, self.doctor_jones.tz)

        available_intervals = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, start_dt_utc, end_dt_utc, self.doctor_jones.tz
        )
        is_available = any(
            interval_start <= start_dt_utc and interval_end >= end_dt_utc # Check if the slot itself is an interval
            for interval_start, interval_end, _ in available_intervals
        )
        # More accurately, check if the desired interval (start_dt_utc, end_dt_utc) is covered by available_intervals
        desired_interval = self.env['resource.calendar.leaves']._Intervals([(start_dt_utc, end_dt_utc, self.env['medical.appointment'])])
        intersection = available_intervals & desired_interval

        self.assertNotEqual(intersection, desired_interval, "Doctor should NOT be available at 8:00 AM.")


    def test_03_doctor_unavailable_on_weekend(self):
        """Check unavailability on a weekend (e.g., Sunday)."""
        test_date = self.today
        while test_date.weekday() != 6: # 6 is Sunday
            test_date += timedelta(days=1)

        # 10:00 AM Denver time on Sunday
        start_dt_utc = self._get_utc_dt(test_date, 10, 0, self.doctor_jones.tz)
        end_dt_utc = self._get_utc_dt(test_date, 11, 0, self.doctor_jones.tz)

        available_intervals = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, start_dt_utc, end_dt_utc, self.doctor_jones.tz
        )
        desired_interval = self.env['resource.calendar.leaves']._Intervals([(start_dt_utc, end_dt_utc, self.env['medical.appointment'])])
        intersection = available_intervals & desired_interval
        self.assertNotEqual(intersection, desired_interval, "Doctor should NOT be available on a Sunday.")

    def test_04_doctor_unavailable_due_to_exception(self):
        """Check unavailability due to a schedule exception (holiday/time off)."""
        test_date = self.today
        while test_date.weekday() != 2: # Wednesday
            test_date += timedelta(days=1)

        # Dr. Jones has a holiday on this Wednesday from 9 AM to 5 PM Denver time
        exception_start_utc = self._get_utc_dt(test_date, 9, 0, self.doctor_jones.tz)
        exception_end_utc = self._get_utc_dt(test_date, 17, 0, self.doctor_jones.tz)

        self.env['medical.doctor.schedule.exception'].create({
            'name': 'Public Holiday',
            'doctor_id': self.doctor_jones.id,
            'date_from': exception_start_utc,
            'date_to': exception_end_utc,
            'company_id': self.env.company.id,
        })

        # Try to check availability at 10:00 AM Denver time on that Wednesday
        check_start_utc = self._get_utc_dt(test_date, 10, 0, self.doctor_jones.tz)
        check_end_utc = self._get_utc_dt(test_date, 11, 0, self.doctor_jones.tz)

        available_intervals = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, check_start_utc, check_end_utc, self.doctor_jones.tz
        )
        desired_interval = self.env['resource.calendar.leaves']._Intervals([(check_start_utc, check_end_utc, self.env['medical.appointment'])])
        intersection = available_intervals & desired_interval
        self.assertNotEqual(intersection, desired_interval, "Doctor should NOT be available due to holiday exception.")

    def test_05_schedule_with_date_to(self):
        """Test a schedule that has an end date."""
        # Schedule for next month only
        next_month_start = (self.today.replace(day=1) + timedelta(days=35)).replace(day=1)
        next_month_end = (next_month_start + timedelta(days=35)).replace(day=1) - timedelta(days=1)

        temp_schedule = self.env['medical.doctor.schedule'].create({
            'doctor_id': self.doctor_jones.id,
            'date_from': next_month_start,
            'date_to': next_month_end, # Ends end of next month
            'attendance_ids': [
                (0, 0, {'name': 'Temp Mon Morning', 'dayofweek': '0', 'hour_from': 10.0, 'hour_to': 12.0})
            ]
        })

        # Day within this temp schedule (first Monday of next month)
        test_day_in_schedule = next_month_start
        while test_day_in_schedule.weekday() != 0: # Find Monday
            test_day_in_schedule += timedelta(days=1)

        # 10:30 AM Denver time on that Monday
        start_dt_utc_valid = self._get_utc_dt(test_day_in_schedule, 10, 30, self.doctor_jones.tz)
        end_dt_utc_valid = self._get_utc_dt(test_day_in_schedule, 11, 30, self.doctor_jones.tz)

        available_valid = temp_schedule._get_combined_schedule_intervals(
            self.doctor_jones, start_dt_utc_valid, end_dt_utc_valid, self.doctor_jones.tz
        )
        desired_valid_interval = self.env['resource.calendar.leaves']._Intervals([(start_dt_utc_valid, end_dt_utc_valid, self.env['medical.appointment'])])
        intersection_valid = available_valid & desired_valid_interval
        self.assertEqual(intersection_valid, desired_valid_interval, "Should be available during temporary schedule.")

        # Day after this temp schedule ends (e.g., first day of month after next_month_end)
        test_day_after_schedule = next_month_end + timedelta(days=1)
        while test_day_after_schedule.weekday() !=0: # Find Monday
             test_day_after_schedule += timedelta(days=1)

        start_dt_utc_invalid = self._get_utc_dt(test_day_after_schedule, 10, 30, self.doctor_jones.tz)
        end_dt_utc_invalid = self._get_utc_dt(test_day_after_schedule, 11, 30, self.doctor_jones.tz)

        available_invalid = temp_schedule._get_combined_schedule_intervals(
             self.doctor_jones, start_dt_utc_invalid, end_dt_utc_invalid, self.doctor_jones.tz
        )
        desired_invalid_interval = self.env['resource.calendar.leaves']._Intervals([(start_dt_utc_invalid, end_dt_utc_invalid, self.env['medical.appointment'])])
        intersection_invalid = available_invalid & desired_invalid_interval
        self.assertNotEqual(intersection_invalid, desired_invalid_interval, "Should NOT be available after temporary schedule ends.")

        # Also check against the main ongoing schedule (self.schedule_jones) for that far future date.
        # If the main schedule is ongoing, the doctor *should* be available then based on *that* schedule.
        # This tests that _get_combined_schedule_intervals is called on the *correct* schedule record.
        available_main_schedule = self.schedule_jones._get_combined_schedule_intervals(
             self.doctor_jones, start_dt_utc_invalid, end_dt_utc_invalid, self.doctor_jones.tz
        )
        # If test_day_after_schedule is a weekday, the main schedule should make them available.
        if test_day_after_schedule.weekday() < 5: # Monday to Friday
            self.assertEqual(available_main_schedule & desired_invalid_interval, desired_invalid_interval,
                             "Should be available based on main schedule for a future weekday.")
        else: # Weekend
            self.assertNotEqual(available_main_schedule & desired_invalid_interval, desired_invalid_interval,
                                "Should NOT be available based on main schedule for a future weekend.")


    def test_06_overlapping_exceptions_constraint(self):
        """Test constraint preventing overlapping exceptions for the same doctor."""
        test_date = self.today
        while test_date.weekday() != 3: # Thursday
            test_date += timedelta(days=1)

        # First exception: 10 AM to 11 AM
        exception1_start_utc = self._get_utc_dt(test_date, 10, 0, self.doctor_jones.tz)
        exception1_end_utc = self._get_utc_dt(test_date, 11, 0, self.doctor_jones.tz)
        self.env['medical.doctor.schedule.exception'].create({
            'name': 'Meeting 1',
            'doctor_id': self.doctor_jones.id,
            'date_from': exception1_start_utc,
            'date_to': exception1_end_utc,
        })

        # Second exception, fully overlapping: 10:30 AM to 11:30 AM
        exception2_start_utc = self._get_utc_dt(test_date, 10, 30, self.doctor_jones.tz)
        exception2_end_utc = self._get_utc_dt(test_date, 11, 30, self.doctor_jones.tz)

        with self.assertRaisesRegex(ValidationError, "overlaps with another existing exception"):
            self.env['medical.doctor.schedule.exception'].create({
                'name': 'Meeting 2 (Overlap)',
                'doctor_id': self.doctor_jones.id,
                'date_from': exception2_start_utc,
                'date_to': exception2_end_utc,
            })

    def test_07_resource_calendar_attendance_link(self):
        """Test that resource.calendar.attendance records are linked to doctor_schedule_id."""
        self.assertTrue(self.schedule_jones.attendance_ids)
        for attendance in self.schedule_jones.attendance_ids:
            self.assertEqual(attendance.doctor_schedule_id, self.schedule_jones)

        # Ensure that if a schedule is deleted, its attendances are also deleted (ondelete='cascade')
        schedule_to_delete = self.env['medical.doctor.schedule'].create({
            'doctor_id': self.doctor_jones.id,
            'date_from': self.today + timedelta(days=30), # Future schedule
            'attendance_ids': [
                (0, 0, {'name': 'Temp Mon Morning', 'dayofweek': '0', 'hour_from': 10.0, 'hour_to': 12.0})
            ]
        })
        attendance_id_to_check = schedule_to_delete.attendance_ids[0].id
        self.assertTrue(self.env['resource.calendar.attendance'].browse(attendance_id_to_check).exists())

        schedule_to_delete.unlink()
        self.assertFalse(self.env['resource.calendar.attendance'].browse(attendance_id_to_check).exists(),
                         "Attendance lines should be deleted when schedule is unlinked due to ondelete='cascade'.")

    # More tests:
    # - Test _compute_name for schedule.
    # - Test multi-company aspects for exceptions and schedules if company_id is used strictly.
    # - Test behavior with different timezones for doctor and querying user.
    # - Test active=False for schedules and exceptions.
    # - Test sql_constraints (e.g., unique doctor+date_from for schedule).
    #   This is harder to test in Python tests unless you try to create violating data.
    #   Example for sql_constraint:
    #   with self.assertRaises(IntegrityError): # odoo.sql_db.IntegrityError
    #       self.env['medical.doctor.schedule'].create({
    #           'doctor_id': self.doctor_jones.id,
    #           'date_from': self.schedule_jones.date_from, # Same doctor, same start date
    #           # ... other fields ...
    #       })
    #   (Requires `from psycopg2 import IntegrityError` or similar, and might depend on DB backend)

    def test_08_schedule_active_toggle(self):
        """Test toggling active field on schedule."""
        self.assertTrue(self.schedule_jones.active)
        self.schedule_jones.toggle_active()
        self.assertFalse(self.schedule_jones.active)

        # Check availability when schedule is inactive
        test_date = self.today
        while test_date.weekday() != 1: # Tuesday
            test_date += timedelta(days=1)
        start_dt_utc = self._get_utc_dt(test_date, 10, 0, self.doctor_jones.tz)
        end_dt_utc = self._get_utc_dt(test_date, 11, 0, self.doctor_jones.tz)

        # The _get_combined_schedule_intervals method itself checks self.active
        available_intervals = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, start_dt_utc, end_dt_utc, self.doctor_jones.tz
        )
        self.assertEqual(len(available_intervals), 0, "Doctor should have no availability if schedule is inactive.")

        self.schedule_jones.toggle_active() # Set back to active for other tests
        self.assertTrue(self.schedule_jones.active)

    def test_09_exception_active_toggle(self):
        """Test toggling active field on exception."""
        test_date = self.today
        while test_date.weekday() != 0: # Monday
            test_date += timedelta(days=1)

        exception_start_utc = self._get_utc_dt(test_date, 9, 0, self.doctor_jones.tz) # 9 AM
        exception_end_utc = self._get_utc_dt(test_date, 17, 0, self.doctor_jones.tz) # 5 PM (all day)

        exception = self.env['medical.doctor.schedule.exception'].create({
            'name': 'Training Day',
            'doctor_id': self.doctor_jones.id,
            'date_from': exception_start_utc,
            'date_to': exception_end_utc,
        })
        self.assertTrue(exception.active)

        # Check availability - should be unavailable at 10 AM due to active exception
        check_start_utc = self._get_utc_dt(test_date, 10, 0, self.doctor_jones.tz)
        check_end_utc = self._get_utc_dt(test_date, 11, 0, self.doctor_jones.tz)
        available_intervals = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, check_start_utc, check_end_utc, self.doctor_jones.tz
        )
        desired_interval = self.env['resource.calendar.leaves']._Intervals([(check_start_utc, check_end_utc, self.env['medical.appointment'])])
        intersection = available_intervals & desired_interval
        self.assertNotEqual(intersection, desired_interval, "Doctor should be unavailable due to active exception.")

        # Deactivate exception
        exception.toggle_active()
        self.assertFalse(exception.active)

        # Re-check availability - should now be available
        available_intervals_after_inactive_exc = self.schedule_jones._get_combined_schedule_intervals(
            self.doctor_jones, check_start_utc, check_end_utc, self.doctor_jones.tz
        )
        intersection_after_inactive = available_intervals_after_inactive_exc & desired_interval
        self.assertEqual(intersection_after_inactive, desired_interval, "Doctor should be available if exception is inactive.")

    def test_10_schedule_name_computation(self):
        """Test the computed name of the schedule."""
        expected_name_part_doctor = f"Schedule for {self.doctor_jones.name}"
        expected_name_part_date = f"from {self.schedule_jones.date_from.strftime('%Y-%m-%d')}"
        self.assertIn(expected_name_part_doctor, self.schedule_jones.name)
        self.assertIn(expected_name_part_date, self.schedule_jones.name)

        # With date_to
        schedule_with_to = self.env['medical.doctor.schedule'].create({
            'doctor_id': self.doctor_jones.id,
            'date_from': self.today,
            'date_to': self.tomorrow,
        })
        expected_name_part_date_to = f"to {self.tomorrow.strftime('%Y-%m-%d')}"
        self.assertIn(expected_name_part_date_to, schedule_with_to.name)
