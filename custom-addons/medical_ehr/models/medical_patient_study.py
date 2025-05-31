# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class MedicalPatientStudy(models.Model):
    _name = 'medical.patient.study'
    _description = 'Patient Medical Study/Test Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'study_date desc, id desc'

    name = fields.Char(string='Study Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, domain="[('is_patient', '=', True)]", tracking=True)
    study_type_id = fields.Many2one('medical.study.type', string='Study Type', required=True, tracking=True)

    requesting_doctor_id = fields.Many2one('res.partner', string='Requesting Doctor', domain="[('is_doctor', '=', True)]", tracking=True)
    performing_lab_id = fields.Many2one('res.partner', string='Performing Lab/Facility', help="Laboratory or facility that performed the study.", tracking=True) # Could be a specific model in future
    consultation_id = fields.Many2one('medical.consultation', string='Originating Consultation', tracking=True)

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, tracking=True)
    study_date = fields.Datetime(string='Study Date/Time', default=fields.Datetime.now, tracking=True, help="Date and time when the study was performed.")

    report_text = fields.Html(string='Report/Results', help="Detailed report or summary of results. Can include formatted text and images.", tracking=True)
    conclusion = fields.Text(string='Conclusion/Summary', help="Brief conclusion or summary of the findings.", tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('scheduled', 'Scheduled'),
        ('performed', 'Performed/In Progress'),
        ('completed', 'Completed/Results Available'),
        ('reviewed', 'Reviewed by Doctor'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean(default=True, tracking=True) # For archiving

    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Documents")

    def _compute_attached_docs_count(self):
        Attachment = self.env['ir.attachment']
        for study in self:
            study.doc_count = Attachment.search_count([
                ('res_model', '=', self._name),
                ('res_id', '=', study.id)
            ])

    # Attachments can be managed via the mail.thread chatter or a dedicated ir.attachment field if needed.
    # For now, relying on chatter for general attachments.

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('medical.patient.study') or _('New')
        return super(MedicalPatientStudy, self).create(vals_list)

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }
