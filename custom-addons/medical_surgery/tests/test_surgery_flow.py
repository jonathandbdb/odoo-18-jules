# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError, AccessError
from datetime import datetime, timedelta

class TestSurgeryFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Models
        cls.Partner = cls.env['res.partner']
        cls.Specialty = cls.env['medical.specialty'] # From medical_appointment
        cls.OperatingRoom = cls.env['medical.operating.room']
        cls.EquipmentType = cls.env['medical.equipment.type']
        cls.SurgicalTeamRole = cls.env['medical.surgical.team.role']
        cls.Surgery = cls.env['medical.surgery']
        cls.SurgeryTeamMember = cls.env['medical.surgery.team_member']
        cls.CalendarEvent = cls.env['calendar.event']

        # Create Specialty
        cls.general_surgery_specialty = cls.Specialty.create({'name': 'General Surgery'})

        # Create Patient
        cls.patient_surgery_test = cls.Partner.create({
            'name': 'Surgery Test Patient',
            'is_patient': True,
        })

        # Create Doctors / Staff (as res.partner)
        cls.surgeon_dr_house = cls.Partner.create({
            'name': 'Dr. Gregory House', 'is_doctor': True,
            'specialty_ids': [(6, 0, [cls.general_surgery_specialty.id])]
        })
        cls.nurse_jane = cls.Partner.create({
            'name': 'Nurse Jane Doe', 'is_doctor': False, # Assuming an 'is_nurse' flag or similar role might be used
            # For now, just a partner. Domain on team_member_id might need adjustment or is_nurse flag.
        })

        # Create Operating Room
        cls.or_01 = cls.OperatingRoom.create({'name': 'Operating Room 1'})

        # Create Equipment Type
        cls.equipment_scalpel_set = cls.EquipmentType.create({'name': 'Scalpel Set'})
        cls.or_01.write({'equipment_ids': [(6, 0, [cls.equipment_scalpel_set.id])]})


        # Create Surgical Team Roles
        cls.role_surgeon = cls.SurgicalTeamRole.create({'name': 'Surgeon', 'code': 'SURG'})
        cls.role_nurse = cls.SurgicalTeamRole.create({'name': 'Scrub Nurse', 'code': 'NURS'})

        # Date/Time for surgery
        cls.planned_start = datetime.now() + timedelta(days=7, hours=9) # Next week 9 AM
        cls.planned_end = cls.planned_start + timedelta(hours=2) # 2 hour surgery

    def test_01_create_surgery_and_calendar_event(self):
        """Test creating a surgery and verifying its linked calendar event."""
        surgery_vals = {
            'patient_id': self.patient_surgery_test.id,
            'operating_room_id': self.or_01.id,
            'planned_start_datetime': self.planned_start,
            'planned_end_datetime': self.planned_end,
            'primary_surgeon_id': self.surgeon_dr_house.id,
            'procedure_name': 'Appendectomy',
            'team_member_ids': [
                (0, 0, {'member_id': self.surgeon_dr_house.id, 'role_id': self.role_surgeon.id}),
                (0, 0, {'member_id': self.nurse_jane.id, 'role_id': self.role_nurse.id}),
            ],
            'status': 'scheduled', # Create directly as scheduled to trigger event creation
        }
        surgery = self.Surgery.create(surgery_vals)
        self.assertTrue(surgery.id, "Surgery should be created.")
        self.assertIn('SURG/', surgery.name, "Surgery sequence name not applied.")

        # Check for calendar event
        self.assertTrue(surgery.calendar_event_id, "Calendar event should be created for a scheduled surgery.")
        self.assertEqual(surgery.calendar_event_id.name,
                         f"Surgery: Appendectomy - {self.patient_surgery_test.name} (OR: {self.or_01.name})")
        self.assertEqual(surgery.calendar_event_id.start, self.planned_start)
        self.assertEqual(surgery.calendar_event_id.stop, self.planned_end)
        self.assertIn(self.patient_surgery_test.id, surgery.calendar_event_id.partner_ids.ids)
        self.assertIn(self.surgeon_dr_house.id, surgery.calendar_event_id.partner_ids.ids)

    def test_02_surgery_status_changes_and_calendar(self):
        """Test status changes of a surgery and their impact on the calendar event."""
        surgery = self.Surgery.create({
            'patient_id': self.patient_surgery_test.id,
            'operating_room_id': self.or_01.id,
            'planned_start_datetime': self.planned_start,
            'planned_end_datetime': self.planned_end,
            'primary_surgeon_id': self.surgeon_dr_house.id,
            'procedure_name': 'Cholecystectomy',
            'status': 'draft', # Start as draft
        })
        self.assertFalse(surgery.calendar_event_id, "Calendar event should not be created for a draft surgery.")

        # Schedule it
        surgery.action_schedule() # Changes status to 'scheduled'
        self.assertEqual(surgery.status, 'scheduled')
        self.assertTrue(surgery.calendar_event_id, "Calendar event should be created when surgery is scheduled.")
        original_event_id = surgery.calendar_event_id.id

        # Confirm it
        surgery.action_confirm()
        self.assertEqual(surgery.status, 'confirmed')
        self.assertTrue(surgery.calendar_event_id, "Calendar event should persist when surgery is confirmed.")
        self.assertEqual(surgery.calendar_event_id.id, original_event_id, "Event ID should remain the same on confirmation.")

        # Start Surgery
        surgery.action_start_surgery()
        self.assertEqual(surgery.status, 'in_progress')
        self.assertIsNotNone(surgery.actual_start_datetime)
        self.assertTrue(surgery.calendar_event_id, "Calendar event should persist when surgery is in progress.")

        # End Surgery
        surgery.action_end_surgery()
        self.assertEqual(surgery.status, 'completed')
        self.assertIsNotNone(surgery.actual_end_datetime)
        self.assertTrue(surgery.calendar_event_id, "Calendar event should persist when surgery is completed.")
        # Optionally, check if event details are updated (e.g. status in description)
        self.assertIn("Status: completed", surgery.calendar_event_id.description)


        # Cancel the surgery
        surgery.action_cancel_surgery() # Changes status to 'cancelled'
        self.assertEqual(surgery.status, 'cancelled')
        self.assertFalse(surgery.calendar_event_id, "Calendar event should be removed when surgery is cancelled.")

        # Check if the event was actually deleted
        self.assertFalse(self.CalendarEvent.search([('id', '=', original_event_id)]), "Calendar event record should be deleted from DB.")

    def test_03_update_surgery_time_updates_calendar(self):
        """Test that updating surgery time also updates the calendar event."""
        surgery = self.Surgery.create({
            'patient_id': self.patient_surgery_test.id,
            'operating_room_id': self.or_01.id,
            'planned_start_datetime': self.planned_start,
            'planned_end_datetime': self.planned_end,
            'primary_surgeon_id': self.surgeon_dr_house.id,
            'procedure_name': 'Hernia Repair',
            'status': 'scheduled',
        })
        self.assertTrue(surgery.calendar_event_id, "Calendar event should exist.")

        new_start_time = self.planned_start + timedelta(hours=1)
        new_end_time = self.planned_end + timedelta(hours=1)

        surgery.write({
            'planned_start_datetime': new_start_time,
            'planned_end_datetime': new_end_time,
        })

        self.assertEqual(surgery.calendar_event_id.start, new_start_time, "Calendar event start time should be updated.")
        self.assertEqual(surgery.calendar_event_id.stop, new_end_time, "Calendar event stop time should be updated.")

    def test_04_delete_surgery_deletes_calendar_event(self):
        """Test that deleting a surgery also deletes its calendar event."""
        surgery = self.Surgery.create({
            'patient_id': self.patient_surgery_test.id,
            'operating_room_id': self.or_01.id,
            'planned_start_datetime': self.planned_start,
            'planned_end_datetime': self.planned_end,
            'procedure_name': 'Tonsillectomy',
            'status': 'scheduled',
        })
        self.assertTrue(surgery.calendar_event_id, "Calendar event must exist before surgery deletion.")
        event_id = surgery.calendar_event_id.id

        surgery.unlink()

        self.assertFalse(self.CalendarEvent.search([('id', '=', event_id)]),
                         "Calendar event should be deleted when the surgery is deleted.")

    def test_05_create_or_config_models(self):
         """Test creation of OR, Equipment Type, Surgical Team Role."""
         self.assertTrue(self.or_01.id)
         self.assertIn(self.equipment_scalpel_set, self.or_01.equipment_ids)
         self.assertTrue(self.equipment_scalpel_set.id)
         self.assertTrue(self.role_surgeon.id)
         self.assertTrue(self.role_nurse.id)
