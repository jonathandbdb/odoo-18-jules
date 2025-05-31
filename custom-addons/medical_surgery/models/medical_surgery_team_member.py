# -*- coding: utf-8 -*-
from odoo import models, fields

class MedicalSurgeryTeamMember(models.Model):
    _name = 'medical.surgery.team_member'
    _description = 'Surgical Team Member Link'
    _order = 'surgery_id, role_id' # Or some other logical order

    surgery_id = fields.Many2one('medical.surgery', string='Surgery', required=True, ondelete='cascade')
    # Using res.partner for flexibility, can be domain restricted to doctors/nurses
    # Or use hr.employee if 'hr' module is a strong dependency and preferred.
    member_id = fields.Many2one('res.partner', string='Team Member', required=True,
                                domain="['|', ('is_doctor', '=', True), ('is_nurse', '=', True)]")
                                # Assumes 'is_nurse' field might be added to res.partner later
    role_id = fields.Many2one('medical.surgical.team.role', string='Role', required=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('surgery_member_role_uniq', 'unique(surgery_id, member_id, role_id)',
         'A team member cannot have the same role multiple times for the same surgery.')
    ]
    # Add a helper on res.partner for is_nurse if needed, similar to is_doctor/is_patient
