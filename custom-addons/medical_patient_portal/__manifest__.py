{
    'name': 'Medical Patient Portal',
    'version': '18.0.1.0.0',
    'summary': 'Provides patients access to their medical information and appointment management via Odoo portal.',
    'description': """
        Extends the Odoo portal to allow patients to:
        - View and manage their upcoming appointments.
        - View parts of their EHR (e.g., prescriptions, lab results after review).
        - Update their personal information.
        - Communicate with the medical center (potentially).
    """,
    'category': 'Services/Medical',
    'author': 'Jules AI',
    'website': 'https://example.com',
    'depends': [
        'portal',               # Odoo's base portal functionality
        'medical_appointment',  # To view/manage appointments
        'medical_ehr',          # To view EHR data (prescriptions, studies, etc.)
        # 'website',            # Often needed for portal pages styling and full features
        # 'account',            # If patients can view/pay invoices through portal
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/medical_patient_portal_security.xml', # Record rules for patient access

        # Views & Templates
        'views/portal_templates_base.xml',
        'views/portal_templates_appointments.xml',
        'views/portal_templates_ehr_summary.xml',
        'views/portal_templates_prescriptions.xml',
        'views/portal_templates_studies.xml',     # Added this line
        'views/portal_templates_ehr.xml',       # Kept for other potential EHR portal parts
        'views/portal_sidebar.xml',
        'views/medical_patient_views_inherited.xml',
        # 'views/assets.xml', # If loading custom CSS/JS specifically for portal (often done in assets block now)
    ],
    'assets': {
        'web.assets_frontend': [
            'medical_patient_portal/static/src/scss/portal_styles.scss', # Example custom SCSS
            # 'medical_patient_portal/static/src/js/portal_custom.js', # Example custom JS
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
