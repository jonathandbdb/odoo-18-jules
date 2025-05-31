{
    'name': 'Medical Electronic Health Record (EHR)',
    'version': '18.0.1.0.0',
    'summary': 'Manages patient electronic health records, including consultations, medical history, and prescriptions.',
    'description': """
        Electronic Health Record (EHR) management for medical facilities.
        - Patient Demographics (extending res.partner)
        - Consultations
        - Medical History (Allergies, Chronic Conditions, Vaccinations)
        - Prescriptions
        - Basic Reporting
    """,
    'category': 'Services/Medical',
    'author': 'Jules AI',
    'website': 'https://example.com',
    'depends': ['medical_appointment', 'product'], # product for medication as products
    'data': [
        'security/ir.model.access.csv',
        'security/medical_ehr_groups.xml', # Specific EHR groups if needed beyond medical_appointment groups
        'views/ehr_views.xml',
        'views/patient_views_inherited.xml', # For EHR specific additions to partner form
        'views/consultation_views.xml',
        'views/prescription_views.xml',
        'views/medical_history_views.xml',
        'views/medical_study_type_views.xml',
        'views/medical_patient_study_views.xml',
        'data/medical_ehr_data.xml', # e.g., allergy types, medication forms
        'reports/prescription_report_templates.xml', # For PDF prescription
        'reports/medical_reports.xml', # Report actions
    ],
    'installable': True,
    'application': False, # Part of the larger medical application suite
    'auto_install': False,
}
