# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_patient = fields.Boolean(string='Is a Patient', default=False, help="Check this box if this contact is a patient.")
    is_doctor = fields.Boolean(string='Is a Doctor', default=False, help="Check this box if this contact is a doctor.")

    # This field is for the medical.doctor model, but since we are inheriting res.partner for doctor,
    # we can define it here and it will be available.
    # Alternatively, define it in medical.doctor and it will be added to res.partner table.
    specialty_ids = fields.Many2many('medical.specialty', string='Specialties', help="Doctor's medical specialties.")

    # Computed fields to control visibility of the flags in the UI based on context/domain
    is_patient_visible = fields.Boolean(compute='_compute_medical_partner_type_visibility')
    is_doctor_visible = fields.Boolean(compute='_compute_medical_partner_type_visibility')

    def _compute_medical_partner_type_visibility(self):
        for partner in self:
            is_patient_context = self.env.context.get('default_is_patient') or self.env.context.get('search_default_is_patient')
            is_doctor_context = self.env.context.get('default_is_doctor') or self.env.context.get('search_default_is_doctor')
            partner.is_patient_visible = bool(is_patient_context) or partner.is_patient
            partner.is_doctor_visible = bool(is_doctor_context) or partner.is_doctor
