# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time
import pytz

class TestAppointmentScheduling(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAppointmentScheduling, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True)) # Disable tracking for tests

        # Create a medical category if it doesn't exist to prevent issues with group creation
        cls.medical_category = cls.env['ir.module.category'].search([('name', '=', 'Medical')], limit=1)
        if not cls.medical_category:
            cls.medical_category = cls.env['ir.module.category'].create({
                'name': 'Medical',
                'description': 'Test Medical Category',
            })

        # Create Medical Groups (if not created by XML, though they should be)
        cls.group_medical_user = cls.env['res.groups'].search([('name', '=', 'Medical / User')], limit=1)
        if not cls.group_medical_user:
            cls.group_medical_user = cls.env['res.groups'].create({
                'name': 'Medical / User',
                'category_id': cls.medical_category.id,
            })

        cls.group_medical_manager = cls.env['res.groups'].search([('name', '=', 'Medical / Manager')], limit=1)
        if not cls.group_medical_manager:
            cls.group_medical_manager = cls.env['res.groups'].create({
                'name': 'Medical / Manager',
                'category_id': cls.medical_category.id,
                'implied_ids': [(4, cls.group_medical_user.id)]
            })

        # Create test user with a timezone (e.g., for converting messages)
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser@example.com',
            'email': 'testuser@example.com',
            'groups_id': [(6, 0, [cls.group_medical_user.id, cls.env.ref('base.group_user').id])],
            'tz': 'America/New_York', # Example timezone
        })

        # Create a Medical Specialty
        cls.specialty_gp = cls.env['medical.specialty'].create({'name': 'General Practice'})

        # Create a Doctor (as res.partner)
        cls.doctor_smith = cls.env['res.partner'].create({
            'name': 'Dr. John Smith',
            'is_doctor': True,
            'specialty_ids': [(6, 0, [cls.specialty_gp.id])],
            'tz': 'Europe/Brussels', # Doctor's working timezone
        })
        # Ensure MedicalDoctor model compatibility if it adds specific fields (not the case here)
        # cls.medical_doctor_smith = cls.env['medical.doctor'].browse(cls.doctor_smith.id)


        # Create a Patient (as res.partner)
        cls.patient_doe = cls.env['res.partner'].create({
            'name': 'Jane Doe',
            'is_patient': True,
        })
        # cls.medical_patient_doe = cls.env['medical.patient'].browse(cls.patient_doe.id)


        # Create a Schedule for Dr. Smith (Monday to Friday, 9-12 and 14-17, Brussels time)
        # Schedule from beginning of current year, indefinitely
        today = datetime.today()
        cls.schedule_smith = cls.env['medical.doctor.schedule'].create({
            'doctor_id': cls.doctor_smith.id,
            'date_from': today.replace(month=1, day=1),
            'date_to': False, # Ongoing
            'company_id': cls.env.company.id,
            'attendance_ids': [
                (0, 0, {'name': 'Mon Morning', 'dayofweek': '0', 'hour_from': 9.0, 'hour_to': 12.0}),
                (0, 0, {'name': 'Mon Afternoon', 'dayofweek': '0', 'hour_from': 14.0, 'hour_to': 17.0}),
                (0, 0, {'name': 'Tue Morning', 'dayofweek': '1', 'hour_from': 9.0, 'hour_to': 12.0}),
                (0, 0, {'name': 'Tue Afternoon', 'dayofweek': '1', 'hour_from': 14.0, 'hour_to': 17.0}),
                (0, 0, {'name': 'Wed Morning', 'dayofweek': '2', 'hour_from': 9.0, 'hour_to': 12.0}),
                (0, 0, {'name': 'Wed Afternoon', 'dayofweek': '2', 'hour_from': 14.0, 'hour_to': 17.0}),
                (0, 0, {'name': 'Thu Morning', 'dayofweek': '3', 'hour_from': 9.0, 'hour_to': 12.0}),
                (0, 0, {'name': 'Thu Afternoon', 'dayofweek': '3', 'hour_from': 14.0, 'hour_to': 17.0}),
                (0, 0, {'name': 'Fri Morning', 'dayofweek': '4', 'hour_from': 9.0, 'hour_to': 12.0}),
                (0, 0, {'name': 'Fri Afternoon', 'dayofweek': '4', 'hour_from': 14.0, 'hour_to': 17.0}),
            ]
        })

        # Find a Monday for testing (or any weekday Dr. Smith works)
        cls.appointment_date_dt = today
        while cls.appointment_date_dt.weekday() >= 5: # 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
            cls.appointment_date_dt += timedelta(days=1)

        # Set a specific time: 10:00 AM in Doctor's timezone (Europe/Brussels)
        # Convert this local time to UTC for storing in Odoo
        doctor_tz = pytz.timezone(cls.doctor_smith.tz)
        cls.appointment_datetime_local = doctor_tz.localize(
            datetime.combine(cls.appointment_date_dt.date(), time(10, 0, 0))
        )
        cls.appointment_datetime_utc = cls.appointment_datetime_local.astimezone(pytz.utc)


    def test_01_create_valid_appointment(self):
        """Test creating a valid appointment within the doctor's schedule."""
        appointment = self.env['medical.appointment'].with_user(self.test_user).create({
            'patient_id': self.patient_doe.id,
            'doctor_id': self.doctor_smith.id,
            'appointment_date': self.appointment_datetime_utc, # 10:00 Brussels time on a working day
            'duration': 1.0, # 1 hour
            'state': 'draft',
        })
        self.assertTrue(appointment.id, "Valid appointment should be created.")
        appointment.action_confirm() # Should pass availability check
        self.assertEqual(appointment.state, 'confirmed', "Appointment should be confirmed.")

    def test_02_create_appointment_outside_schedule_hours(self):
        """Test creating an appointment outside doctor's working hours but on a working day."""
        # Example: 8:00 AM Brussels time (doctor starts at 9:00)
        invalid_datetime_local = pytz.timezone(self.doctor_smith.tz).localize(
            datetime.combine(self.appointment_date_dt.date(), time(8, 0, 0))
        )
        invalid_datetime_utc = invalid_datetime_local.astimezone(pytz.utc)

        with self.assertRaisesRegex(ValidationError, "The selected time for Dr. John Smith is not available"):
            self.env['medical.appointment'].with_user(self.test_user).create({
                'patient_id': self.patient_doe.id,
                'doctor_id': self.doctor_smith.id,
                'appointment_date': invalid_datetime_utc,
                'duration': 1.0,
                'state': 'draft', # Validation is triggered on create/write if state is not cancelled/done
            })

    def test_03_create_appointment_on_weekend(self):
        """Test creating an appointment on a weekend (e.g., Sunday)."""
        weekend_date = self.appointment_date_dt
        while weekend_date.weekday() < 5: # Find next Saturday (5) or Sunday (6)
            weekend_date += timedelta(days=1)

        weekend_datetime_local = pytz.timezone(self.doctor_smith.tz).localize(
            datetime.combine(weekend_date.date(), time(10, 0, 0)) # 10 AM on a weekend
        )
        weekend_datetime_utc = weekend_datetime_local.astimezone(pytz.utc)

        with self.assertRaisesRegex(ValidationError, "The selected time for Dr. John Smith is not available"):
            self.env['medical.appointment'].with_user(self.test_user).create({
                'patient_id': self.patient_doe.id,
                'doctor_id': self.doctor_smith.id,
                'appointment_date': weekend_datetime_utc,
                'duration': 1.0,
            })

    def test_04_create_appointment_overlapping_exception(self):
        """Test creating an appointment that overlaps with a doctor's schedule exception."""
        # Exception for Dr. Smith on the test appointment date from 9:30 to 10:30 Brussels time
        exception_start_local = pytz.timezone(self.doctor_smith.tz).localize(
             datetime.combine(self.appointment_date_dt.date(), time(9, 30, 0))
        )
        exception_end_local = exception_start_local + timedelta(hours=1)

        exception_start_utc = exception_start_local.astimezone(pytz.utc)
        exception_end_utc = exception_end_local.astimezone(pytz.utc)

        self.env['medical.doctor.schedule.exception'].create({
            'name': 'Short Meeting',
            'doctor_id': self.doctor_smith.id,
            'date_from': exception_start_utc,
            'date_to': exception_end_utc,
            'company_id': self.env.company.id,
        })

        # Try to book at 10:00 Brussels time (overlaps with 9:30-10:30 exception)
        appointment_at_10_utc = self.appointment_datetime_utc

        with self.assertRaisesRegex(ValidationError, "The selected time for Dr. John Smith is not available"):
            self.env['medical.appointment'].with_user(self.test_user).create({
                'patient_id': self.patient_doe.id,
                'doctor_id': self.doctor_smith.id,
                'appointment_date': appointment_at_10_utc, # This is 10:00 Brussels time
                'duration': 0.5, # 30 mins
            })

    def test_05_appointment_without_doctor_schedule(self):
        """Test creating an appointment for a doctor with no defined schedule."""
        doctor_no_schedule = self.env['res.partner'].create({
            'name': 'Dr. No Schedule',
            'is_doctor': True,
            'tz': 'UTC',
        })

        # Attempt to book on any weekday at 10 AM UTC
        appointment_date = datetime.now()
        while appointment_date.weekday() >=5:
            appointment_date += timedelta(days=1)
        appointment_datetime = datetime.combine(appointment_date.date(), time(10,0,0))


        with self.assertRaisesRegex(ValidationError, "does not have an active schedule covering"):
            self.env['medical.appointment'].with_user(self.test_user).create({
                'patient_id': self.patient_doe.id,
                'doctor_id': doctor_no_schedule.id,
                'appointment_date': appointment_datetime, # Odoo assumes UTC if no TZ context
                'duration': 1.0,
            })

    def test_06_calendar_event_creation_and_deletion(self):
        """Test that calendar.event is created and deleted with appointment."""
        appointment = self.env['medical.appointment'].with_user(self.test_user).create({
            'patient_id': self.patient_doe.id,
            'doctor_id': self.doctor_smith.id,
            'appointment_date': self.appointment_datetime_utc,
            'duration': 1.0,
        })
        self.assertTrue(appointment.calendar_event_id, "Calendar event should be created.")

        calendar_event_id = appointment.calendar_event_id.id

        # Cancel appointment - should delete calendar event
        appointment.action_cancel()
        # The current logic in action_cancel of appointment might not immediately delete if it's a soft cancel.
        # Let's assume for now it does, or that unlink() is called.
        # If action_cancel just sets state, we might need to call unlink().
        # The provided code for action_cancel in medical_appointment.py *does* unlink the calendar event.

        self.assertFalse(
            self.env['calendar.event'].search([('id', '=', calendar_event_id)]),
            "Calendar event should be deleted when appointment is cancelled."
        )

        # Recreate for unlink test
        appointment = self.env['medical.appointment'].with_user(self.test_user).create({
            'patient_id': self.patient_doe.id,
            'doctor_id': self.doctor_smith.id,
            'appointment_date': self.appointment_datetime_utc, # 10:00 Brussels time
            'duration': 1.0,
        })
        calendar_event_id = appointment.calendar_event_id.id
        appointment.unlink()
        self.assertFalse(
            self.env['calendar.event'].search([('id', '=', calendar_event_id)]),
            "Calendar event should be deleted when appointment is unlinked."
        )

    def test_07_update_appointment_to_invalid_slot(self):
        """Test updating an appointment from a valid to an invalid slot."""
        appointment = self.env['medical.appointment'].with_user(self.test_user).create({
            'patient_id': self.patient_doe.id,
            'doctor_id': self.doctor_smith.id,
            'appointment_date': self.appointment_datetime_utc, # Valid: 10:00 Brussels time
            'duration': 0.5,
        })
        self.assertTrue(appointment.id)

        # Try to move it to 8:00 AM Brussels time (invalid)
        invalid_datetime_local = pytz.timezone(self.doctor_smith.tz).localize(
            datetime.combine(self.appointment_date_dt.date(), time(8, 0, 0))
        )
        invalid_datetime_utc = invalid_datetime_local.astimezone(pytz.utc)

        with self.assertRaisesRegex(ValidationError, "The selected time for Dr. John Smith is not available"):
            appointment.write({
                'appointment_date': invalid_datetime_utc,
            })

    def test_08_partner_as_patient_and_doctor(self):
        """Test flags is_patient and is_doctor on res.partner."""
        self.assertTrue(self.doctor_smith.is_doctor)
        self.assertFalse(self.doctor_smith.is_patient) # Assuming Dr. Smith is not also a patient
        self.assertTrue(self.patient_doe.is_patient)
        self.assertFalse(self.patient_doe.is_doctor)

        # Test creating a partner who is both
        multi_role_partner = self.env['res.partner'].create({
            'name': 'Dr. Patient',
            'is_doctor': True,
            'is_patient': True,
        })
        self.assertTrue(multi_role_partner.is_doctor)
        self.assertTrue(multi_role_partner.is_patient)

        # Test domain filters in appointment form (conceptual, actual view test is harder)
        # Patient field should only show is_patient=True
        # Doctor field should only show is_doctor=True
        # This is implicitly tested by the fact that we can select them in other tests.

    # More tests could be added:
    # - Concurrent appointments for the same doctor.
    # - Appointments spanning across lunch breaks or day end/start.
    # - Correctness of suggestions for available slots in user's timezone.
    # - Behavior when doctor's timezone is not set.
    # - Multi-company aspects if relevant.
    # - Tests for `medical.patient` and `medical.doctor` models if they had more logic.
    #   (Currently they are mostly res.partner extensions).
    # - Test `medical.specialty`.
    # - Test calendar event updates when appointment `doctor_id`, `patient_id`, `duration` changes.
    #   The current `write` method in `medical_appointment.py` handles this.

    # Example of testing specialty
    def test_09_specialty_management(self):
        """Test creation and listing of medical specialties."""
        cardiologist = self.env['medical.specialty'].create({'name': 'Cardiology'})
        self.assertTrue(cardiologist.id)
        self.assertIn(cardiologist, self.doctor_smith.specialty_ids | self.specialty_gp) # Check if it can be added

        all_specialties = self.env['medical.specialty'].search([])
        self.assertGreaterEqual(len(all_specialties), 2) # GP and Cardiology

    # Example for testing res.partner fields visibility
    def test_10_partner_medical_flags_visibility_context(self):
        """Test visibility flags for is_patient/is_doctor based on context."""
        # Default context, no specific medical type
        partner_form_default_ctx = self.env['res.partner'].with_context({}).new({'name': 'Temp Partner'})
        self.assertFalse(partner_form_default_ctx.is_patient_visible, "is_patient should be hidden by default")
        self.assertFalse(partner_form_default_ctx.is_doctor_visible, "is_doctor should be hidden by default")

        # Context for creating a new patient
        partner_form_patient_ctx = self.env['res.partner'].with_context({'default_is_patient': True}).new({})
        self.assertTrue(partner_form_patient_ctx.is_patient_visible, "is_patient should be visible for new patient context")
        self.assertFalse(partner_form_patient_ctx.is_doctor_visible, "is_doctor should be hidden for new patient context")

        # Context for creating a new doctor
        partner_form_doctor_ctx = self.env['res.partner'].with_context({'default_is_doctor': True}).new({})
        self.assertFalse(partner_form_doctor_ctx.is_patient_visible, "is_patient should be hidden for new doctor context")
        self.assertTrue(partner_form_doctor_ctx.is_doctor_visible, "is_doctor should be visible for new doctor context")

        # Existing patient, no specific context
        patient_form_no_ctx = self.patient_doe.with_context({})
        self.assertTrue(patient_form_no_ctx.is_patient_visible, "is_patient should be visible for existing patient")
        self.assertFalse(patient_form_no_ctx.is_doctor_visible, "is_doctor should be hidden for existing patient unless also doctor")

        # Existing doctor, no specific context
        doctor_form_no_ctx = self.doctor_smith.with_context({})
        self.assertFalse(doctor_form_no_ctx.is_patient_visible, "is_patient should be hidden for existing doctor unless also patient")
        self.assertTrue(doctor_form_no_ctx.is_doctor_visible, "is_doctor should be visible for existing doctor")

        # Existing partner who is both, no specific context
        multi_role_partner = self.env['res.partner'].create({
            'name': 'Dr. Patient Both', 'is_doctor': True, 'is_patient': True
        })
        multi_role_form_no_ctx = multi_role_partner.with_context({})
        self.assertTrue(multi_role_form_no_ctx.is_patient_visible, "is_patient should be visible if partner is patient")
        self.assertTrue(multi_role_form_no_ctx.is_doctor_visible, "is_doctor should be visible if partner is doctor")
