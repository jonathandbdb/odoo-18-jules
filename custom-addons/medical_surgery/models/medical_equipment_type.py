# -*- coding: utf-8 -*-
from odoo import models, fields

class MedicalEquipmentType(models.Model):
    _name = 'medical.equipment.type'
    _description = 'Type of Medical Equipment for OR'
    _order = 'name'

    name = fields.Char(string='Equipment Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Equipment type name must be unique.')
    ]
