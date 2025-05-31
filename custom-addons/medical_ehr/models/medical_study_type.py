# -*- coding: utf-8 -*-
from odoo import models, fields

class MedicalStudyType(models.Model):
    _name = 'medical.study.type'
    _description = 'Type of Medical Study (e.g., Lab, Imaging)'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', help="Optional code for the study type, e.g., LOINC for lab tests.")
    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Study type name must be unique.'),
        ('code_uniq', 'unique(code)', 'Study type code must be unique if provided.')
    ]
