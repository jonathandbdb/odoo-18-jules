# -*- coding: utf-8 -*-
from odoo import http, _, fields # Add fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError # Ensure these are imported
from odoo.osv.expression import OR
from odoo.tools import groupby as groupbyelem # For grouping if needed
from operator import itemgetter # For grouping if needed
from datetime import datetime, date # Ensure date is imported

class CustomerPortalEHR(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortalEHR, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        # Consolidate counts for layout from various controllers if needed, or keep them specific.
        # For now, this controller might primarily add its own specific counts if any.
        # Counts for appointments, prescriptions, studies are handled in their respective templates/controllers or portal_layout extension
        partner = request.env.user.partner_id
        prescription_count = request.env['medical.prescription'].search_count([
            ('patient_id', '=', partner.id),
            ('state', 'in', ['active', 'dispensed', 'expired']) # Matching portal rule
        ]) if hasattr(partner, 'is_patient') and partner.is_patient else 0

        study_count = request.env['medical.patient.study'].search_count([
            ('patient_id', '=', partner.id),
            ('status', 'in', ['completed', 'reviewed']) # Matching portal rule
        ]) if hasattr(partner, 'is_patient') and partner.is_patient else 0

        values.update({
            'prescription_count': prescription_count,
            'study_count': study_count, # Add study count
            'medical_area': True,
        })
        return values

    # --- Clinical History Summary ---
    @http.route(['/my/medical/history', '/my/medical/history/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_clinical_history(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        if not hasattr(partner, 'is_patient') or not partner.is_patient:
            # Redirect or show error if user is not a patient
            return request.render("medical_patient_portal.portal_not_a_patient_error_page", values)


        Consultation = request.env['medical.consultation']
        ChronicCondition = request.env['medical.patient.chronic.condition']
        Allergy = request.env['medical.patient.allergy']

        # Domain for consultations
        consultation_domain = [('patient_id', '=', partner.id)]
        # Pager for consultations
        consultations_count = Consultation.search_count(consultation_domain)
        consultations_pager = portal_pager(
            url="/my/medical/history",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=consultations_count,
            page=page,
            step=5 # Show 5 consultations per page for summary
        )
        consultations = Consultation.search(
            consultation_domain,
            order='consultation_date desc',
            limit=5,
            offset=consultations_pager['offset']
        )

        # Active Chronic Conditions
        chronic_conditions = ChronicCondition.search([
            ('patient_id', '=', partner.id),
            ('status', '=', 'active')
        ])

        # Allergies
        allergies = Allergy.search([
            ('patient_id', '=', partner.id),
            ('active', '=', True)
        ])

        values.update({
            'consultations': consultations,
            'consultations_pager': consultations_pager,
            'consultations_pager_values': {'url': '/my/medical/history', 'total': consultations_count, 'page': page, 'step': 5}, # For pager template
            'chronic_conditions': chronic_conditions,
            'allergies': allergies,
            'page_name': 'clinical_history', # For sidebar active state
            'medical_area': True,
        })
        return request.render("medical_patient_portal.portal_my_clinical_history_summary", values)

    # Placeholder for a consultation detail page if linked from summary
    @http.route(['/my/medical/consultation/<int:consultation_id>'], type='http', auth="user", website=True)
    def portal_my_consultation_detail(self, consultation_id, access_token=None, **kw):
        try:
            consultation_sudo = self._document_check_access('medical.consultation', consultation_id, access_token)
        except (AccessError, MissingError): # Ensure these exceptions are imported
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        values.update({
            'consultation': consultation_sudo,
            'page_name': 'consultation_detail',
            'medical_area': True,
        })
        # You would need a specific template for this, e.g., "portal_consultation_detail_page"
        # For now, this is a placeholder and might reuse a generic detail view or error if template not made.
        # return request.render("medical_patient_portal.portal_consultation_detail_page", values)
        return request.make_response("Consultation detail page not yet implemented.", status=501)


    # --- Prescriptions List ---
    def _get_prescription_searchbar_sortings(self):
        return {
            'date_desc': {'label': _('Newest Date'), 'order': 'prescription_date desc, id desc'},
            'date_asc': {'label': _('Oldest Date'), 'order': 'prescription_date asc, id asc'},
            'name_asc': {'label': _('Reference'), 'order': 'name asc'},
            'status': {'label': _('Status'), 'order': 'state asc'},
        }

    def _get_prescription_searchbar_filters(self):
        return {
            'all': {'label': _('All'), 'domain': []}, # Will be combined with patient + state domain
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'dispensed': {'label': _('Dispensed'), 'domain': [('state', '=', 'dispensed')]},
            'expired': {'label': _('Expired'), 'domain': [('state', '=', 'expired')]},
        }

    @http.route(['/my/medical/prescriptions', '/my/medical/prescriptions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_prescriptions(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Prescription = request.env['medical.prescription']

        if not hasattr(partner, 'is_patient') or not partner.is_patient:
            return request.render("medical_patient_portal.portal_not_a_patient_error_page", values)

        domain = [
            ('patient_id', '=', partner.id),
            ('state', 'in', ['active', 'dispensed', 'expired']) # Base domain from security rule
        ]

        searchbar_sortings = self._get_prescription_searchbar_sortings()
        searchbar_filters = self._get_prescription_searchbar_filters()

        if not sortby:
            sortby = 'date_desc'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end: # Example date filter on prescription_date
            domain += [('prescription_date', '>=', date_begin), ('prescription_date', '<=', date_end)]

        if search and search_in: # Basic search on prescription name/ID
            if search_in == 'all' or search_in == 'name':
                 domain += [('name', 'ilike', search)]
            # Add more fields to search if needed, e.g., medication name from lines (more complex)

        prescription_count = Prescription.search_count(domain)
        pager_values = {
            'url': "/my/medical/prescriptions",
            'url_args': {'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            'total': prescription_count,
            'page': page,
            'step': self._items_per_page
        }
        pager = portal_pager(**pager_values)

        prescriptions = Prescription.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_prescriptions_history'] = prescriptions.ids[:100]

        values.update({
            'prescriptions': prescriptions,
            'page_name': 'prescriptions',
            'pager': pager,
            'default_url': '/my/medical/prescriptions',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            'medical_area': True,
        })
        return request.render("medical_patient_portal.portal_my_prescriptions_list", values)

    # --- Prescription Detail & Download ---
    @http.route(['/my/medical/prescription/<int:prescription_id>'], type='http', auth="user", website=True)
    def portal_my_prescription_detail(self, prescription_id, access_token=None, **kw):
        try:
            prescription_sudo = self._document_check_access('medical.prescription', prescription_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        values.update({
            'prescription': prescription_sudo,
            'page_name': 'prescription_detail',
            'medical_area': True,
        })
        # You would need a specific template: "medical_patient_portal.portal_prescription_detail_page"
        return request.render("medical_patient_portal.portal_prescription_detail_page", values)


    @http.route(['/my/medical/prescription/pdf/<int:prescription_id>'], type='http', auth="user", website=True)
    def portal_my_prescription_report(self, prescription_id, access_token=None, **kw):
        try:
            prescription_sudo = self._document_check_access('medical.prescription', prescription_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Check if the report action exists (created in medical_ehr module)
        report_action = request.env.ref('medical_ehr.action_report_medical_prescription', False)
        if not report_action:
            return request.make_response("Prescription report configuration not found.", status=500)

        pdf_content, content_type = report_action._render_qweb_pdf(prescription_sudo.ids)

        pdf_http_headers = [
            ('Content-Type', content_type),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'attachment; filename="Prescription_{prescription_sudo.name or prescription_sudo.id}.pdf";')
        ]
        return request.make_response(pdf_content, headers=pdf_http_headers)


# Note: The "portal_not_a_patient_error_page" template should be in an XML file.
# The route below is just a simple way to make it callable if not defined elsewhere.
# It's better to handle this check within each medical route or via inherited _prepare_portal_layout_values.

# @http.route('/my/medical/access_error', type='http', auth="user", website=True)
# def medical_portal_access_error(self, **kw):
#    return request.render("medical_patient_portal.portal_not_a_patient_error_page")

# Removing the global http.route for portal_not_a_patient to keep controller class-focused.
# Error handling should be part of each relevant route or a general portal check.
# The template "portal_not_a_patient_error_page" will be in an XML file.
# <template id="portal_not_a_patient_error_page" name="Not a Patient Error">
#   <t t-call="portal.portal_layout">
#     <div class="container">
#       <div class="alert alert-danger mt-3" role="alert">
#         <h4>Access Denied</h4>
#         <p>You are not registered as a patient in our system.
#            If you believe this is an error, please contact the medical center administration.</p>
#       </div>
#     </div>
#   </t>
# </template>

    # --- Medical Studies List ---
    def _get_study_searchbar_sortings(self):
        return {
            'date_desc': {'label': _('Newest Date'), 'order': 'study_date desc, id desc'},
            'date_asc': {'label': _('Oldest Date'), 'order': 'study_date asc, id asc'},
            'type': {'label': _('Study Type'), 'order': 'study_type_id asc'},
            'status': {'label': _('Status'), 'order': 'status asc'},
        }

    def _get_study_searchbar_filters(self):
        # Domain matches the ir.rule for portal users
        return {
            'all': {'label': _('All'), 'domain': [('status', 'in', ['completed', 'reviewed'])]},
            'completed': {'label': _('Completed'), 'domain': [('status', '=', 'completed')]},
            'reviewed': {'label': _('Reviewed'), 'domain': [('status', '=', 'reviewed')]},
        }

    @http.route(['/my/medical/studies', '/my/medical/studies/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_studies(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PatientStudy = request.env['medical.patient.study']

        if not hasattr(partner, 'is_patient') or not partner.is_patient:
            return request.render("medical_patient_portal.portal_not_a_patient_error_page", values)

        # Base domain from security rule for studies
        domain = [('patient_id', '=', partner.id), ('status', 'in', ['completed', 'reviewed'])]

        searchbar_sortings = self._get_study_searchbar_sortings()
        searchbar_filters = self._get_study_searchbar_filters()

        if not sortby:
            sortby = 'date_desc'
        order = searchbar_sortings[sortby]['order']

        if not filterby: # Default filter is 'all' (which itself filters by completed/reviewed)
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end: # Example date filter on study_date
            domain += [('study_date', '>=', date_begin), ('study_date', '<=', date_end)]

        if search and search_in:
            if search_in == 'all' or search_in == 'type':
                 domain += [('study_type_id.name', 'ilike', search)]
            if search_in == 'all' or search_in == 'name': # Search in study reference/name
                 domain += [('name', 'ilike', search)]


        study_count = PatientStudy.search_count(domain)
        pager_values = {
            'url': "/my/medical/studies",
            'url_args': {'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            'total': study_count,
            'page': page,
            'step': self._items_per_page
        }
        pager = portal_pager(**pager_values)

        studies = PatientStudy.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_studies_history'] = studies.ids[:100]

        values.update({
            'studies': studies,
            'page_name': 'studies',
            'pager': pager,
            'default_url': '/my/medical/studies',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            'medical_area': True,
        })
        return request.render("medical_patient_portal.portal_my_studies_list", values)

    # --- Study Detail & Attachment Download ---
    @http.route(['/my/medical/study/<int:study_id>'], type='http', auth="user", website=True)
    def portal_my_study_detail(self, study_id, access_token=None, **kw):
        try:
            study_sudo = self._document_check_access('medical.patient.study', study_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Fetch attachments linked to this study
        attachments = request.env['ir.attachment'].search([
            ('res_model', '=', 'medical.patient.study'),
            ('res_id', '=', study_sudo.id)
        ])

        values = self._prepare_portal_layout_values()
        values.update({
            'study': study_sudo,
            'attachments': attachments,
            'page_name': 'study_detail',
            'medical_area': True,
        })
        return request.render("medical_patient_portal.portal_study_detail_page", values)

    @http.route(['/my/medical/study/attachment/<int:attachment_id>'], type='http', auth="user", website=True)
    def portal_my_study_attachment_download(self, attachment_id, access_token=None, **kw):
        Attachment = request.env['ir.attachment']
        try:
            attachment_sudo = self._document_check_access('ir.attachment', attachment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Security check: Ensure the attachment belongs to a study the user has access to
        if attachment_sudo.res_model != 'medical.patient.study' or not attachment_sudo.res_id:
            raise AccessError(_("Invalid attachment link."))

        study_sudo = request.env['medical.patient.study'].browse(attachment_sudo.res_id).sudo()
        if not study_sudo.exists() or study_sudo.patient_id != request.env.user.partner_id:
             raise AccessError(_("You do not have access to this medical study or its attachments."))

        if study_sudo.status not in ['completed', 'reviewed']: # Match ir.rule for study visibility
            raise AccessError(_("This study's results are not yet available for viewing."))

        return self._show_report(model=attachment_sudo, report_type='pdf', report_ref=None, download=True)
