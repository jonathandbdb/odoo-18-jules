# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PatientEHR(models.Model):
    _inherit = 'res.partner' # Inheriting from res.partner to add EHR specific fields

    # Example EHR-specific fields for a patient:
    blood_type = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ], string='Blood Type')

    ehr_notes = fields.Text(string='EHR General Notes')

    # Link to consultations, history, etc. will be via One2many from here
    # or Many2one from those models pointing to res.partner (patient).
    consultation_ids = fields.One2many('medical.consultation', 'patient_id', string='Consultations')
    prescription_ids = fields.One2many('medical.prescription', 'patient_id', string='Prescriptions')
    consultation_count = fields.Integer(compute='_compute_medical_record_counts', string="Consultations")
    prescription_count = fields.Integer(compute='_compute_medical_record_counts', string="Prescriptions")

    # Medical History (could also be separate models linked here)
    allergy_ids = fields.One2many('medical.patient.allergy', 'patient_id', string='Allergies')
    chronic_condition_ids = fields.One2many('medical.patient.chronic.condition', 'patient_id', string='Chronic Conditions')
    vaccination_ids = fields.One2many('medical.patient.vaccination', 'patient_id', string='Vaccinations')

    # Computed field to easily identify if a partner has EHR data or is "activated" in EHR
    has_ehr_data = fields.Boolean(string="Has EHR Records", compute="_compute_has_ehr_data", store=True)

    @api.depends('consultation_ids', 'prescription_ids', 'allergy_ids', 'chronic_condition_ids', 'vaccination_ids', 'blood_type', 'ehr_notes')
    def _compute_has_ehr_data(self):
        for patient in self:
            patient.has_ehr_data = bool(
                patient.consultation_ids or \
                patient.prescription_ids or \
                patient.allergy_ids or \
                patient.chronic_condition_ids or \
                patient.vaccination_ids or \
                patient.blood_type or \
                patient.ehr_notes
            )

    def _compute_medical_record_counts(self):
        for patient in self:
            patient.consultation_count = len(patient.consultation_ids)
            patient.prescription_count = len(patient.prescription_ids)
            # Counts for allergies, conditions, etc. could be added if needed for stat buttons

    def action_view_ehr_summary(self):
        # Placeholder for an action to view a comprehensive EHR summary report or view
        self.ensure_one()
        # This could open a wizard or a specific form view with all EHR info
        return {
            'name': f"EHR Summary for {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner', # Or a custom wizard model
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current', # Or 'new' for a dialog/wizard
            # 'context': {'ehr_summary_view': True} # To load a specific view if needed
        }
