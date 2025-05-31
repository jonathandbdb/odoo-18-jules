# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class MedicalConsultation(models.Model):
    _name = 'medical.consultation'
    _description = 'Medical Consultation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'consultation_date desc, id desc'

    name = fields.Char(string='Consultation Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, domain="[('is_patient', '=', True)]", tracking=True)
    doctor_id = fields.Many2one('res.partner', string='Doctor', required=True, domain="[('is_doctor', '=', True)]", tracking=True)
    appointment_id = fields.Many2one('medical.appointment', string='Linked Appointment', tracking=True)

    consultation_date = fields.Datetime(string='Consultation Date', required=True, default=fields.Datetime.now, tracking=True)

    diagnosis = fields.Text(string='Diagnosis', tracking=True)
    symptoms = fields.Text(string='Symptoms Reported', tracking=True)
    findings = fields.Text(string='Clinical Findings', tracking=True)
    treatment_plan = fields.Text(string='Treatment Plan', tracking=True)
    notes = fields.Text(string='Additional Notes')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True, tracking=True)

    # Link to prescriptions created from this consultation
    prescription_ids = fields.One2many('medical.prescription', 'consultation_id', string='Prescriptions Issued')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('medical.consultation') or _('New')
        return super(MedicalConsultation, self).create(vals_list)

    def action_view_prescriptions(self):
        self.ensure_one()
        return {
            'name': _('Prescriptions'),
            'type': 'ir.actions.act_window',
            'res_model': 'medical.prescription',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.prescription_ids.ids)],
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_consultation_id': self.id,
            }
        }

    def action_create_prescription(self):
        self.ensure_one()
        return {
            'name': _('New Prescription'),
            'type': 'ir.actions.act_window',
            'res_model': 'medical.prescription',
            'view_mode': 'form',
            'target': 'new', # Open in a dialog
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_consultation_id': self.id,
            }
        }
