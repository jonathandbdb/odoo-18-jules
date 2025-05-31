# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MedicalPrescription(models.Model):
    _name = 'medical.prescription'
    _description = 'Medical Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'prescription_date desc, id desc'

    name = fields.Char(string='Prescription ID', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, domain="[('is_patient', '=', True)]", tracking=True)
    doctor_id = fields.Many2one('res.partner', string='Prescribing Doctor', required=True, domain="[('is_doctor', '=', True)]", tracking=True)
    consultation_id = fields.Many2one('medical.consultation', string='Originating Consultation', tracking=True)

    prescription_date = fields.Date(string='Prescription Date', required=True, default=fields.Date.context_today, tracking=True)
    notes = fields.Text(string='General Notes for Pharmacist/Patient')

    prescription_line_ids = fields.One2many('medical.prescription.line', 'prescription_id', string='Medications', copy=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'), # Active and can be dispensed
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('dispensed', 'Fully Dispensed'), # Optional: if tracking dispensing status
    ], string='Status', default='draft', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True, tracking=True) # For archiving

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('medical.prescription') or _('New')
        return super(MedicalPrescription, self).create(vals_list)

    def action_activate(self):
        if not self.prescription_line_ids:
            raise UserError(_("Cannot activate a prescription with no medication lines."))
        self.write({'state': 'active'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_print_prescription(self):
        self.ensure_one()
        # This will refer to an ir.actions.report defined in XML
        return self.env.ref('medical_ehr.action_report_medical_prescription').report_action(self)


class MedicalPrescriptionLine(models.Model):
    _name = 'medical.prescription.line'
    _description = 'Medical Prescription Line (Medication)'

    prescription_id = fields.Many2one('medical.prescription', string='Prescription', required=True, ondelete='cascade')
    medication_id = fields.Many2one('product.product', string='Medication', required=True,
                                    domain="[('type', '=', 'consu'), ('is_medicament', '=', True)]") # Assuming 'consu' type for consumables/drugs
                                                                                                   # and a custom 'is_medicament' field on product.product

    dosage = fields.Char(string='Dosage', help="e.g., 1 tablet, 10ml, 2 puffs")
    frequency = fields.Char(string='Frequency', help="e.g., Twice a day, Every 4 hours, As needed")
    duration = fields.Char(string='Duration', help="e.g., 7 days, For 1 month, Until finished")
    route_id = fields.Many2one('medical.medication.route', string='Route', help="e.g., Oral, Topical, IV")
    form_id = fields.Many2one('medical.medication.form', string='Form', help="e.g., Tablet, Syrup, Inhaler")

    quantity = fields.Float(string='Quantity to Dispense', default=1.0)
    notes = fields.Text(string='Instructions/Notes for this specific medication')

    # Related fields from medication for display or easier access (optional)
    medication_name = fields.Char(related='medication_id.name', string='Medication Name', readonly=True)

    # Ensure is_medicament is on product template and product.product
    # (Similar to is_vaccine in medical_history.py)
    # This is just a reference; actual field addition is in another file or assumed to be there.

# Add 'is_medicament' to product.template and product.product if not already done by another module
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    is_medicament = fields.Boolean(string='Is a Medicament?', default=False, help="Check if this product is a medicament/drug.")

class ProductProduct(models.Model):
    _inherit = 'product.product'
    # is_medicament is related from product.template via product_tmpl_id
    pass


class MedicalMedicationRoute(models.Model):
    _name = 'medical.medication.route'
    _description = 'Medication Administration Route'
    _order = 'name'

    name = fields.Char(string='Route Name', required=True, index=True)
    code = fields.Char(string='Code', help="e.g., SNOMED CT code or internal code")
    description = fields.Text(string='Description')
    _sql_constraints = [('name_uniq', 'unique(name)', 'Route name must be unique.')]


class MedicalMedicationForm(models.Model):
    _name = 'medical.medication.form'
    _description = 'Medication Form (e.g., Tablet, Syrup)'
    _order = 'name'

    name = fields.Char(string='Form Name', required=True, index=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    _sql_constraints = [('name_uniq', 'unique(name)', 'Form name must be unique.')]
