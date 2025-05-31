# -*- coding: utf-8 -*-
from odoo import models, fields

class MedicalSurgicalTeamRole(models.Model):
    _name = 'medical.surgical.team.role'
    _description = 'Role in a Surgical Team'
    _order = 'name'

    name = fields.Char(string='Role Name', required=True, translate=True)
    code = fields.Char(string='Role Code')
    description = fields.Text(string='Description', translate=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Surgical team role name must be unique.'),
        ('code_uniq', 'unique(code)', 'Surgical team role code must be unique if provided.')
    ]
