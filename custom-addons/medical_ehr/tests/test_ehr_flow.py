# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
import pytz

class TestEHRFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestEHRFlow, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Ensure Medical Category and Groups are available (from medical_appointment)
        cls.medical_category = cls.env.ref('medical_appointment.base.module_category_services_medical', raise_if_not_found=False)
        if not cls.medical_category: # Should exist from medical_appointment's data
            cls.medical_category = cls.env['ir.module.category'].create({'name': 'Medical', 'sequence': 25})

        cls.group_medical_user = cls.env.ref('medical_appointment.group_medical_user', raise_if_not_found=False)
        if not cls.group_medical_user:
            cls.group_medical_user = cls.env['res.groups'].create({
                'name': 'Medical / User', 'category_id': cls.medical_category.id
            })

        cls.group_medical_manager = cls.env.ref('medical_appointment.group_medical_manager', raise_if_not_found=False)
        if not cls.group_medical_manager:
             cls.group_medical_manager = cls.env['res.groups'].create({
                'name': 'Medical / Manager',
                'category_id': cls.medical_category.id,
                'implied_ids': [(4, cls.group_medical_user.id)]
            })


        # Test User
        cls.test_user_doctor = cls.env['res.users'].create({
            'name': 'Test EHR Doctor',
            'login': 'testdocehr@example.com',
            'email': 'testdocehr@example.com',
            'groups_id': [(6, 0, [cls.group_medical_user.id, cls.group_medical_manager.id, cls.env.ref('base.group_user').id])],
            'tz': 'Europe/London',
        })

        # Patient
        cls.patient_ehr_test = cls.env['res.partner'].create({
            'name': 'EHR Test Patient',
            'is_patient': True,
            'birthdate_date': date(1985, 5, 15), # For age calculation in report
            'blood_type': 'O+',
        })

        # Doctor (also a res.partner)
        cls.doctor_ehr_test = cls.env['res.partner'].create({
            'name': 'Dr. EHR Test',
            'is_doctor': True,
            'user_id': cls.test_user_doctor.id, # Link to user for some functionalities
            'tz': 'Europe/London',
        })

        # Data for Medical History and Prescriptions
        cls.allergy_type_penicillin = cls.env.ref('medical_ehr.allergy_type_penicillin', raise_if_not_found=False) \
            or cls.env['medical.allergy.type'].create({'name': 'Penicillin Test', 'category': 'drug'})

        cls.condition_hypertension = cls.env.ref('medical_ehr.condition_code_hypertension', raise_if_not_found=False) \
            or cls.env['medical.condition.code'].create({'name': 'Hypertension Test', 'code': 'I10Test', 'system': 'ICD-10'})

        cls.vaccine_flu = cls.env.ref('medical_ehr.product_vaccine_flu', raise_if_not_found=False) \
            or cls.env['product.template'].create({
                'name': 'Flu Vaccine Test', 'type': 'consu', 'is_vaccine': True, 'list_price': 15.0
            }).product_variant_id

        cls.medication_amoxicillin = cls.env.ref('medical_ehr.product_med_amoxicillin_250', raise_if_not_found=False) \
            or cls.env['product.template'].create({
                'name': 'Amoxicillin 250mg Test', 'type': 'consu', 'is_medicament': True, 'list_price': 10.0
            }).product_variant_id

        cls.med_route_oral = cls.env.ref('medical_ehr.med_route_oral', raise_if_not_found=False) \
            or cls.env['medical.medication.route'].create({'name': 'Oral Test', 'code': 'POTEST'})

        cls.med_form_tablet = cls.env.ref('medical_ehr.med_form_tablet', raise_if_not_found=False) \
            or cls.env['medical.medication.form'].create({'name': 'Tablet Test'})

        # For Medical Study tests
        cls.StudyType = cls.env['medical.study.type']
        cls.PatientStudy = cls.env['medical.patient.study']
        cls.Attachment = cls.env['ir.attachment']

        cls.study_type_blood = cls.StudyType.create({
            'name': 'Blood Test',
            'code': 'LAB-BLOOD',
        })
        cls.study_type_xray = cls.StudyType.create({
            'name': 'X-Ray',
            'code': 'IMG-XRAY',
        })

        # Model Aliases for convenience
        cls.Consultation = cls.env['medical.consultation']
        cls.Prescription = cls.env['medical.prescription']
        cls.PatientAllergy = cls.env['medical.patient.allergy']
        cls.PatientChronicCondition = cls.env['medical.patient.chronic.condition']
        cls.PatientVaccination = cls.env['medical.patient.vaccination']


    def test_01_create_consultation(self):
        """Test creating a medical consultation."""
        consultation = self.Consultation.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': self.patient_ehr_test.id,
            'doctor_id': self.doctor_ehr_test.id,
            'consultation_date': datetime.now(),
            'symptoms': 'Fever and cough.',
            'diagnosis': 'Suspected flu.',
            'treatment_plan': 'Rest and hydration. Follow up if symptoms worsen.',
        })
        self.assertTrue(consultation.id, "Consultation should be created.")
        self.assertNotEqual(consultation.name, 'New', "Consultation reference should be generated.")
        self.assertEqual(consultation.patient_id, self.patient_ehr_test)
        # Invalidate cache to ensure computed fields are re-calculated
        self.patient_ehr_test.invalidate_cache(ids=[self.patient_ehr_test.id])
        self.assertEqual(self.patient_ehr_test.consultation_count, 1)

    def test_02_add_medical_history(self):
        """Test adding various types of medical history to a patient."""
        # Allergy
        allergy = self.PatientAllergy.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': self.patient_ehr_test.id,
            'allergy_type_id': self.allergy_type_penicillin.id,
            'reaction': 'Rash',
            'criticality': 'medium',
        })
        self.assertTrue(allergy.id, "Allergy record should be created.")
        self.assertIn(allergy, self.patient_ehr_test.allergy_ids)

        # Chronic Condition
        chronic = self.PatientChronicCondition.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': self.patient_ehr_test.id,
            'condition_id': self.condition_hypertension.id,
            'status': 'active',
            'onset_date': date(2020, 1, 1),
        })
        self.assertTrue(chronic.id, "Chronic condition record should be created.")
        self.assertIn(chronic, self.patient_ehr_test.chronic_condition_ids)

        # Vaccination
        vaccination = self.PatientVaccination.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': self.patient_ehr_test.id,
            'vaccine_product_id': self.vaccine_flu.id,
            'effective_date': date.today() - timedelta(days=30), # Vaccinated 30 days ago
            'dose_number': '1st',
            'lot_number': 'LOT123FLU',
        })
        self.assertTrue(vaccination.id, "Vaccination record should be created.")
        self.assertIn(vaccination, self.patient_ehr_test.vaccination_ids)

        self.patient_ehr_test.invalidate_cache(ids=[self.patient_ehr_test.id])
        self.assertTrue(self.patient_ehr_test.has_ehr_data, "Patient should have EHR data flag set.")


    def test_03_create_prescription_from_consultation(self): # Renamed from test_03 to avoid conflict
        """Test creating a prescription from a consultation."""
        consultation = self.Consultation.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': self.patient_ehr_test.id,
            'doctor_id': self.doctor_ehr_test.id,
            'consultation_date': datetime.now(),
            'diagnosis': 'Bacterial Infection',
        })

        # Use action to get context for prescription
        action = consultation.action_create_prescription()
        self.assertIn('default_consultation_id', action.get('context', {}))

        prescription = self.Prescription.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': consultation.patient_id.id,
            'doctor_id': consultation.doctor_id.id,
            'consultation_id': consultation.id, # Link to the consultation
            'prescription_date': date.today(),
            'prescription_line_ids': [(0, 0, {
                'medication_id': self.medication_amoxicillin.id, # Ensure this is product.product
                'dosage': '1 tablet',
                'frequency': 'TID (Three times a day)',
                'duration': '7 days',
                'route_id': self.med_route_oral.id,
                'form_id': self.med_form_tablet.id,
                'quantity': 21,
            })]
        })
        self.assertTrue(prescription.id, "Prescription should be created.")
        self.assertNotEqual(prescription.name, 'New', "Prescription ID should be generated.")
        self.assertEqual(prescription.consultation_id, consultation)
        self.assertIn(prescription, consultation.prescription_ids)

        self.patient_ehr_test.invalidate_cache(ids=[self.patient_ehr_test.id])
        self.assertEqual(self.patient_ehr_test.prescription_count, 1)

        # Test activating prescription
        with self.assertRaises(UserError, msg="Cannot activate with no lines - this should not raise if lines exist"):
             empty_presc = self.Prescription.with_user(self.test_user_doctor).create({ # Use alias
                'patient_id': consultation.patient_id.id, 'doctor_id': consultation.doctor_id.id
             })
             empty_presc.action_activate()

        prescription.action_activate()
        self.assertEqual(prescription.state, 'active', "Prescription should be active.")

    def test_04_prescription_report(self): # Renamed
        """Test generating the prescription report (does not check content, just action)."""
        prescription = self.Prescription.with_user(self.test_user_doctor).create({ # Use alias
            'patient_id': self.patient_ehr_test.id,
            'doctor_id': self.doctor_ehr_test.id,
            'prescription_date': date.today(),
            'state': 'active',
            'prescription_line_ids': [(0, 0, {
                'medication_id': self.medication_amoxicillin.id, # Ensure this is product.product
                'dosage': '1 tablet', 'frequency': 'BID', 'duration': '10 days', 'quantity': 20
            })]
        })
        report_action = prescription.action_print_prescription()
        self.assertIsNotNone(report_action, "Report action should be returned.")
        self.assertEqual(report_action['type'], 'ir.actions.report')
        self.assertEqual(report_action['report_name'], 'medical_ehr.report_medical_prescription_document')

    def test_05_ehr_fields_on_patient(self): # Renamed
        """Test EHR specific fields added to res.partner."""
        self.assertEqual(self.patient_ehr_test.blood_type, 'O+')
        self.patient_ehr_test.write({'ehr_notes': 'Patient is generally healthy.'})
        self.assertEqual(self.patient_ehr_test.ehr_notes, 'Patient is generally healthy.')

        self.patient_ehr_test.invalidate_cache(ids=[self.patient_ehr_test.id])
        self.assertTrue(self.patient_ehr_test.has_ehr_data,
                        "Patient with blood type or history should have has_ehr_data = True.")
        self.assertFalse(self.env['res.partner'].create({'name': 'New Patient'}).has_ehr_data)


    def test_06_product_flags_is_vaccine_is_medicament(self): # Renamed
        """Test the boolean flags on product model."""
        self.assertTrue(self.vaccine_flu.product_tmpl_id.is_vaccine) # vaccine_flu is product.product
        self.assertFalse(self.vaccine_flu.product_tmpl_id.is_medicament)

        self.assertTrue(self.medication_amoxicillin.product_tmpl_id.is_medicament) # medication_amoxicillin is product.product
        self.assertFalse(self.medication_amoxicillin.product_tmpl_id.is_vaccine)


    def test_07_ehr_summary_action_on_patient(self): # Renamed
        """Test the action_view_ehr_summary on res.partner."""
        action = self.patient_ehr_test.action_view_ehr_summary()
        self.assertIsNotNone(action)
        self.assertEqual(action.get('res_model'), 'res.partner')
        self.assertEqual(action.get('res_id'), self.patient_ehr_test.id)


    def test_08_sequences(self): # Renamed
        """Test sequence generation for consultation and prescription."""
        consult_name = self.env['ir.sequence'].next_by_code('medical.consultation')
        self.assertTrue(consult_name.startswith('CONS/'))

        presc_name = self.env['ir.sequence'].next_by_code('medical.prescription')
        self.assertTrue(presc_name.startswith('PRES/'))

    # --- New Test Methods for Medical Study ---

    def test_09_medical_study_creation_and_attachment(self): # New test number
        """Test creating a medical study, linking it, and attachment handling."""
        self.assertTrue(self.study_type_blood.id, "Blood Test study type not created in setup.")

        consultation = self.Consultation.create({ # Use patient_ehr_test
            'patient_id': self.patient_ehr_test.id,
            'doctor_id': self.doctor_ehr_test.id,
            'consultation_date': datetime.now(),
            'diagnosis': 'Routine Checkup for Study',
        })
        self.assertTrue(consultation.id)

        # 1. Create a Medical Patient Study
        study_vals = {
            'patient_id': self.patient_ehr_test.id,
            'study_type_id': self.study_type_blood.id,
            'requesting_doctor_id': self.doctor_ehr_test.id,
            'consultation_id': consultation.id,
            'request_date': datetime.now().date(),
            'study_date': datetime.now(),
            'report_text': '<p>Results are normal.</p>',
            'conclusion': 'No abnormalities detected.',
            'status': 'completed',
        }
        patient_study = self.PatientStudy.create(study_vals)
        self.assertTrue(patient_study.id, "Medical Patient Study should be created.")
        self.assertEqual(patient_study.patient_id, self.patient_ehr_test)
        self.assertEqual(patient_study.study_type_id, self.study_type_blood)
        self.assertIn('STDY/', patient_study.name, "Patient Study sequence name not applied.")

        # 2. Test attachment creation
        attachment = self.Attachment.create({
            'name': 'lab_results.pdf',
            'datas': 'UEsDBAoAAAAAANFUz1IAAAAAAAAAAAAAAA fabbylux'.encode('utf-8'),
            'res_model': patient_study._name,
            'res_id': patient_study.id,
        })
        self.assertTrue(attachment.id, "Attachment should be created.")

        patient_study.invalidate_cache(ids=[patient_study.id])
        self.assertEqual(patient_study.doc_count, 1, "Document count on study should be 1.")

        action_attachments = patient_study.action_view_attachments()
        self.assertIsNotNone(action_attachments, "action_view_attachments should return an action.")
        self.assertEqual(action_attachments['res_model'], 'ir.attachment')
        self.assertIn(('res_id', '=', patient_study.id), action_attachments['domain'])


        # 3. Verify study_count on patient record
        self.patient_ehr_test.invalidate_cache(ids=[self.patient_ehr_test.id])
        initial_study_count = self.patient_ehr_test.study_count # Should be 1 now

        study2 = self.PatientStudy.create({
            'patient_id': self.patient_ehr_test.id,
            'study_type_id': self.study_type_xray.id,
            'request_date': datetime.now().date(),
            'status': 'requested',
        })
        self.assertTrue(study2.id)

        self.patient_ehr_test.invalidate_cache(ids=[self.patient_ehr_test.id])
        self.assertEqual(self.patient_ehr_test.study_count, initial_study_count + 1, "Patient study_count should have incremented.")

        self.assertIn(patient_study, self.patient_ehr_test.study_ids)
        self.assertIn(study2, self.patient_ehr_test.study_ids)

    def test_10_study_type_creation(self): # New test number
        """Test creation of medical study types and constraints."""
        self.assertTrue(self.study_type_blood.id)
        self.assertTrue(self.study_type_xray.id)

        with self.assertRaises(Exception):
            self.StudyType.create({'name': 'Blood Test', 'code': 'LAB-BLOOD-DUP'})

        with self.assertRaises(Exception):
            self.StudyType.create({'name': 'Some Other Test', 'code': 'LAB-BLOOD'})

        new_type = self.StudyType.create({'name': 'Ultrasound Test'}) # Ensure unique name
        self.assertTrue(new_type.id)
        self.assertFalse(new_type.code)
