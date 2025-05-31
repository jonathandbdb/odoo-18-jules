# -*- coding: utf-8 -*-
from odoo import models, fields, api, _ # Ensure _ is imported

class MedicalSurgery(models.Model):
    _name = 'medical.surgery'
    _description = 'Medical Surgery Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_start_datetime desc, id desc'

    name = fields.Char(string='Surgery Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, domain="[('is_patient', '=', True)]", tracking=True)
    operating_room_id = fields.Many2one('medical.operating.room', string='Operating Room', tracking=True)
    originating_consultation_id = fields.Many2one(
        'medical.consultation',
        string='Originating Consultation',
        ondelete='set null',
        tracking=True,
        help="Consultation that recommended or led to this surgery."
    )

    planned_start_datetime = fields.Datetime(string='Planned Start', required=True, tracking=True)
    planned_end_datetime = fields.Datetime(string='Planned End', required=True, tracking=True)
    actual_start_datetime = fields.Datetime(string='Actual Start', readonly=True, tracking=True)
    actual_end_datetime = fields.Datetime(string='Actual End', readonly=True, tracking=True)

    primary_surgeon_id = fields.Many2one('res.partner', string='Primary Surgeon', domain="[('is_doctor', '=', True)]", tracking=True)
    team_member_ids = fields.One2many('medical.surgery.team_member', 'surgery_id', string='Surgical Team')

    procedure_name = fields.Char(string='Procedure Name', required=True, tracking=True)
    pre_operative_diagnosis_ids = fields.Many2many('medical.condition.code',
                                               'surgery_pre_op_diag_rel',
                                               'surgery_id', 'condition_id',
                                               string='Pre-operative Diagnoses')
    post_operative_diagnosis_ids = fields.Many2many('medical.condition.code',
                                                 'surgery_post_op_diag_rel',
                                                 'surgery_id', 'condition_id',
                                                 string='Post-operative Diagnoses')

    operative_notes = fields.Html(string='Operative Notes', tracking=True)
    anesthesia_notes = fields.Html(string='Anesthesia Notes', tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    pre_operative_notes = fields.Html(string='Pre-operative Checklist/Notes')
    post_operative_instructions = fields.Html(string='Post-operative Care Instructions')

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Surgery reference must be unique per company!')
    ]

    # Calendar Integration Methods
    def _get_calendar_event_partner_ids(self):
        self.ensure_one()
        partners = self.env['res.partner']
        if self.patient_id:
            partners |= self.patient_id
        if self.primary_surgeon_id:
            partners |= self.primary_surgeon_id
        return partners.ids

    def _prepare_calendar_event_values(self):
        self.ensure_one()
        partners = self._get_calendar_event_partner_ids()

        name = _("Surgery: %s - %s") % (self.procedure_name or _('N/A'), self.patient_id.name or _('N/A'))
        if self.operating_room_id:
            name += _(" (OR: %s)") % self.operating_room_id.name

        description = _("Procedure: %s\nPatient: %s\nSurgeon: %s\nOR: %s\nStatus: %s") % (
           self.procedure_name or '',
           self.patient_id.name or '',
           self.primary_surgeon_id.name or _('Not Set'),
           self.operating_room_id.name or _('Not Set'),
           self.status # Consider using self.display_status or similar if status is technical
        )
        if self.operative_notes and isinstance(self.operative_notes, str): # Basic check for notes content
           description += _("\n\nOperative Notes Snippet:\n") + self.operative_notes[:200] + "..."

        user_id_to_assign = self.env.user.id # Default to current user
        if self.primary_surgeon_id and self.primary_surgeon_id.user_id:
            user_id_to_assign = self.primary_surgeon_id.user_id.id
        elif self.primary_surgeon_id and self.primary_surgeon_id.user_ids: # Fallback if user_id not set but user_ids (O2M) is
            user_id_to_assign = self.primary_surgeon_id.user_ids[0].id

        return {
            'name': name,
            'start': self.planned_start_datetime,
            'stop': self.planned_end_datetime,
            'allday': False,
            'partner_ids': [(6, 0, partners)],
            'user_id': user_id_to_assign,
            'description': description,
            'location': self.operating_room_id.name if self.operating_room_id else False,
            'res_id': self.id,
            'res_model': self._name,
        }

    def _synchronize_calendar_event(self):
        for surgery in self: # Iterate to handle batch operations if any
            if surgery.planned_start_datetime and surgery.planned_end_datetime and surgery.status not in ['draft', 'cancelled']:
                event_vals = surgery._prepare_calendar_event_values()
                if surgery.calendar_event_id:
                    event_vals.pop('res_model', None)
                    event_vals.pop('res_id', None)
                    try:
                        surgery.calendar_event_id.write(event_vals)
                    except Exception: # Catch broad exception if calendar event was deleted manually
                        surgery.calendar_event_id = False # Clear link
                        new_event = self.env['calendar.event'].create(surgery._prepare_calendar_event_values()) # Recreate
                        surgery.write({'calendar_event_id': new_event.id})
                else:
                    new_event = self.env['calendar.event'].create(event_vals)
                    # Use direct SQL update for calendar_event_id to avoid recursion if write calls sync
                    self.env.cr.execute("UPDATE medical_surgery SET calendar_event_id = %s WHERE id = %s", (new_event.id, surgery.id))
                    surgery.invalidate_cache(ids=[surgery.id])

            elif surgery.calendar_event_id: # If status is draft/cancelled or dates are missing, remove event
                try:
                    surgery.calendar_event_id.unlink()
                except Exception: # Catch broad exception if event already deleted
                    pass # Event is already gone
                surgery.calendar_event_id = False # Clear the link using direct SQL to avoid recursion
                self.env.cr.execute("UPDATE medical_surgery SET calendar_event_id = NULL WHERE id = %s", (surgery.id,))
                surgery.invalidate_cache(ids=[surgery.id])


    @api.model_create_multi
    def create(self, vals_list):
        surgeries = super(MedicalSurgery, self).create(vals_list)
        for i, surgery in enumerate(surgeries): # Iterate with index for vals_list
            # Check initial status from vals_list for the specific surgery record
            # The vals_list might have different values for batch creation
            current_vals = vals_list[i] if i < len(vals_list) else {} # Get corresponding vals or empty dict
            if current_vals.get('status', 'draft') not in ['draft', 'cancelled']:
                 surgery._synchronize_calendar_event()
        return surgeries

    def write(self, vals):
        res = super(MedicalSurgery, self).write(vals)
        relevant_fields = ['planned_start_datetime', 'planned_end_datetime', 'operating_room_id',
                           'patient_id', 'primary_surgeon_id', 'procedure_name', 'status', 'operative_notes', 'active']
        if any(field in vals for field in relevant_fields) or (vals.get('active') is False and self.calendar_event_id):
            if vals.get('active') is False: # If archiving surgery, remove calendar event
                for surgery in self.filtered('calendar_event_id'):
                    try:
                        surgery.calendar_event_id.unlink()
                    except Exception: # Event might already be deleted
                        pass
                    # Use direct SQL update to avoid recursion
                    self.env.cr.execute("UPDATE medical_surgery SET calendar_event_id = NULL WHERE id = %s", (surgery.id,))
                    surgery.invalidate_cache(ids=[surgery.id])
            else:
                # For other changes, synchronize. Ensure self is iterable (it is from write).
                for surgery in self:
                    surgery._synchronize_calendar_event()
        return res

    def unlink(self):
        self.mapped('calendar_event_id').unlink()
        return super(MedicalSurgery, self).unlink()

    # Status actions
    def action_schedule(self):
        self.write({'status': 'scheduled'})

    def action_confirm(self):
        self.write({'status': 'confirmed'})

    def action_start_surgery(self):
        self.write({'status': 'in_progress', 'actual_start_datetime': fields.Datetime.now()})

    def action_end_surgery(self):
        self.write({'status': 'completed', 'actual_end_datetime': fields.Datetime.now()})

    def action_cancel_surgery(self):
        self.write({'status': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'status': 'draft'})
