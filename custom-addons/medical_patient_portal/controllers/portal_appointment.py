# -*- coding: utf-8 -*-
from collections import OrderedDict
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv.expression import OR
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
from datetime import datetime, date

class CustomerPortalAppointments(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortalAppointments, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        appointment_count = request.env['medical.appointment'].search_count([
            ('patient_id', '=', partner.id)
        ]) if partner.is_patient else 0 # Assuming is_patient field exists

        values.update({
            'appointment_count': appointment_count,
            'medical_area': True, # To highlight medical section in sidebar
        })
        return values

    def _get_appointment_searchbar_sortings(self):
        return {
            'date_desc': {'label': _('Newest Date'), 'order': 'appointment_date desc'},
            'date_asc': {'label': _('Oldest Date'), 'order': 'appointment_date asc'},
            'doctor': {'label': _('Doctor'), 'order': 'doctor_id asc'},
            'status': {'label': _('Status'), 'order': 'state asc'},
        }

    def _get_appointment_searchbar_filters(self):
        return {
            'all': {'label': _('All'), 'domain': []},
            'upcoming': {'label': _('Upcoming'), 'domain': [('appointment_date', '>=', datetime.now())]},
            'past': {'label': _('Past'), 'domain': [('appointment_date', '<', datetime.now())]},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }

    def _get_appointment_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('all', 'procedure'): # Assuming 'procedure' is not a direct field, might be notes or related model
            search_domain = OR([search_domain, [('notes', 'ilike', search)]]) # Example: search in notes
        if search_in in ('all', 'doctor'):
            search_domain = OR([search_domain, [('doctor_id.name', 'ilike', search)]])
        if search_in in ('all', 'patient'): # Should not be needed if portal user is always the patient
            search_domain = OR([search_domain, [('patient_id.name', 'ilike', search)]])
        return search_domain


    @http.route(['/my/medical/appointments', '/my/medical/appointments/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointments(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Appointment = request.env['medical.appointment']

        domain = [('patient_id', '=', partner.id)]

        searchbar_sortings = self._get_appointment_searchbar_sortings()
        searchbar_filters = self._get_appointment_searchbar_filters()

        # default sortby order
        if not sortby:
            sortby = 'date_desc'
        order = searchbar_sortings[sortby]['order']

        # default filterby value
        if not filterby:
            filterby = 'upcoming' # Default to upcoming appointments
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)] # Example, adjust field if needed

        # search
        if search and search_in:
            domain += self._get_appointment_search_domain(search_in, search)

        # count for pager
        appointment_count = Appointment.search_count(domain)

        # pager
        pager = portal_pager(
            url="/my/medical/appointments",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=appointment_count,
            page=page,
            step=self._items_per_page
        )

        appointments = Appointment.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_appointments_history'] = appointments.ids[:100]

        # Grouping (example, not fully implemented in provided template snippet but good for backend)
        # if groupby == 'doctor':
        #     grouped_appointments = [Appointment.concat(*g) for k, g in groupbyelem(appointments, itemgetter('doctor_id'))]
        # else:
        #     grouped_appointments = [appointments]

        # Pass 'is_patient' to template if available on res.partner
        is_patient = hasattr(partner, 'is_patient') and partner.is_patient

        values.update({
            'date': date_begin, # For keeping search criteria in template
            'appointments': appointments,
            # 'grouped_appointments': grouped_appointments, # If using grouping
            'page_name': 'appointments',
            'pager': pager,
            'default_url': '/my/medical/appointments',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            # 'groupby': groupby, # If using grouping
            'is_patient': is_patient, # To conditionally show content in template
        })
        return request.render("medical_patient_portal.portal_my_appointments_list", values)

    # Optional: Route for individual appointment details (if needed beyond basic list)
    @http.route(['/my/medical/appointment/<int:appointment_id>'], type='http', auth="user", website=True)
    def portal_my_appointment_detail(self, appointment_id, access_token=None, **kw):
        try:
            appointment_sudo = self._document_check_access('medical.appointment', appointment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._prepare_portal_layout_values() # Get base layout values
        values.update({
            'appointment': appointment_sudo,
            'page_name': 'appointment_detail', # Or a more specific name
            'medical_area': True,
        })
        # Add breadcrumb or history
        history = request.session.get('my_appointments_history', [])
        values.update(self._get_portal_history_breadcrumbs(history, appointment_sudo, AppointmentBreadcrumb))

        return request.render("medical_patient_portal.portal_appointment_detail_page", values) # Requires a new template

# Helper class for breadcrumbs, if using the detail page
class AppointmentBreadcrumb:
    def __init__(self, appointment):
        self.appointment = appointment
    def get_portal_breadcrumb_part(self):
        return {'title': self.appointment.name or _('Appointment'), 'url': f'/my/medical/appointment/{self.appointment.id}'}

# Ensure this class is correctly imported in your __init__.py for controllers
# from . import portal_appointment (or whatever the filename is)
