# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

# Abstract model for common history elements
class MedicalHistoryAbstract(models.AbstractModel):
    _name = 'medical.history.abstract'
    _description = 'Abstract Medical History Item'
    _order = 'effective_date desc, id desc'

    patient_id = fields.Many2one('res.partner', string='Patient', required=True, ondelete='cascade', domain="[('is_patient', '=', True)]")
    effective_date = fields.Date(string='Effective Date', default=fields.Date.context_today, tracking=True)
    notes = fields.Text(string='Notes')
    recorded_by_id = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True, tracking=True)


class MedicalPatientAllergy(models.Model):
    _name = 'medical.patient.allergy'
    _description = 'Patient Allergy Information'
    _inherit = 'medical.history.abstract'

    allergy_type_id = fields.Many2one('medical.allergy.type', string='Allergen/Type', required=True)
    reaction = fields.Char(string='Reaction Severity/Type', help="e.g., Mild Rash, Anaphylaxis")
    criticality = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Criticality', default='medium', tracking=True)

    name = fields.Char(compute='_compute_name', store=True, readonly=True)

    @api.depends('patient_id', 'allergy_type_id', 'effective_date')
    def _compute_name(self):
        for record in self:
            record.name = _("Allergy for %s: %s") % (record.patient_id.name or 'N/A', record.allergy_type_id.name or 'N/A')


class MedicalAllergyType(models.Model):
    _name = 'medical.allergy.type'
    _description = 'Type of Medical Allergy/Allergen'
    _order = 'name'

    name = fields.Char(string='Allergen/Type Name', required=True, index=True)
    description = fields.Text(string='Description')
    category = fields.Selection([
        ('drug', 'Drug Allergy'),
        ('food', 'Food Allergy'),
        ('environmental', 'Environmental Allergy'),
        ('other', 'Other')
    ], string='Category', default='other')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Allergy type name must be unique.')
    ]


class MedicalPatientChronicCondition(models.Model):
    _name = 'medical.patient.chronic.condition'
    _description = 'Patient Chronic Condition'
    _inherit = 'medical.history.abstract'

    condition_id = fields.Many2one('medical.condition.code', string='Condition', required=True) # e.g., ICD-10, SNOMED
    onset_date = fields.Date(string='Date of Onset')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive/Resolved'),
        ('remission', 'In Remission')
    ], string='Status', default='active', tracking=True)

    name = fields.Char(compute='_compute_name', store=True, readonly=True)

    @api.depends('patient_id', 'condition_id', 'effective_date')
    def _compute_name(self):
        for record in self:
            record.name = _("Condition for %s: %s") % (record.patient_id.name or 'N/A', record.condition_id.name or 'N/A')


class MedicalConditionCode(models.Model):
    _name = 'medical.condition.code'
    _description = 'Medical Condition Code (e.g., ICD-10)'
    _order = 'code, name'

    name = fields.Char(string='Condition Name', required=True, index=True)
    code = fields.Char(string='Code', required=True, index=True)
    system = fields.Char(string='Coding System', default='ICD-10', help="e.g., ICD-10, SNOMED-CT")
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_system_uniq', 'unique(code, system)', 'Condition code must be unique per coding system.')
    ]

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            if record.system:
                name = f"({record.system}) {name}"
            result.append((record.id, name))
        return result


class MedicalPatientVaccination(models.Model):
    _name = 'medical.patient.vaccination'
    _description = 'Patient Vaccination Record'
    _inherit = 'medical.history.abstract' # effective_date here is vaccination date

    vaccine_product_id = fields.Many2one('product.product', string='Vaccine Administered',
                                         domain="[('is_vaccine', '=', True)]", # Requires 'is_vaccine' on product.product
                                         required=True)
    lot_number = fields.Char(string='Lot Number')
    expiration_date = fields.Date(string='Expiration Date')
    dose_number = fields.Char(string='Dose', help="e.g., 1st, 2nd, Booster")
    administered_by_id = fields.Many2one('res.partner', string='Administered By (Clinician/Facility)', domain="[('is_doctor', '=', True)]") # or make it a User
    next_dose_due_date = fields.Date(string='Next Dose Due')

    name = fields.Char(compute='_compute_name', store=True, readonly=True)

    @api.depends('patient_id', 'vaccine_product_id', 'effective_date')
    def _compute_name(self):
        for record in self:
            record.name = _("Vaccination for %s: %s on %s") % (
                record.patient_id.name or 'N/A',
                record.vaccine_product_id.name or 'N/A',
                fields.Date.to_string(record.effective_date) if record.effective_date else 'N/A'
            )

# Add 'is_vaccine' to product.template and product.product
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    is_vaccine = fields.Boolean(string='Is a Vaccine?', default=False, help="Check if this product is a vaccine.")

class ProductProduct(models.Model):
    _inherit = 'product.product'
    # is_vaccine is related from product.template
    pass
