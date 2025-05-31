# -*- coding: utf-8 -*-
from odoo import models, fields

class MedicalOperatingRoom(models.Model):
    _name = 'medical.operating.room'
    _description = 'Operating Room'
    _order = 'name'

    name = fields.Char(string='Room Name/Number', required=True)
    description = fields.Text(string='Description')
    equipment_ids = fields.Many2many(
        'medical.equipment.type',
        'operating_room_equipment_type_rel',
        'operating_room_id',
        'equipment_type_id',
        string='Available Equipment'
    )
    active = fields.Boolean(default=True, help="Set to false to archive the OR.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Operating Room name must be unique per company!')
    ]
