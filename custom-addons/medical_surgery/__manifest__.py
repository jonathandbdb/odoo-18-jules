{
    'name': 'Medical Surgery Management',
    'version': '18.0.1.0.0',
    'summary': 'Manage surgical procedures, operating room schedules, and surgical teams.',
    'description': """
        Module for managing surgical operations, including:
        - Surgery definition and types
        - Pre-operative and post-operative checklists
        - Operating room (OR) scheduling and availability
        - Surgical team management (surgeons, nurses, anesthesiologists)
        - Integration with patient EHR and appointments
    """,
    'category': 'Services/Medical',
    'author': 'Jules AI',
    'website': 'https://example.com',
    'depends': [
        'medical_ehr',      # For patient information, consultations leading to surgery
        'calendar',         # For OR scheduling, potentially surgeon availability
        'hr',               # For managing surgical team members (employees)
        # 'stock',          # Optional: for managing surgical supplies, implants
        # 'account',        # Optional: for billing of surgical procedures
    ],
    'data': [
        'security/ir.model.access.csv', # Will be added in a later step
        'security/medical_surgery_groups.xml', # If specific surgery roles are needed
        'data/medical_surgery_data.xml',
        'views/medical_surgery_config_views.xml',
        'views/medical_operating_room_views.xml',
        'views/medical_surgery_views.xml',
        'views/medical_surgery_menus.xml',
        # 'views/surgery_type_views.xml', # This was a placeholder, actual models are equipment & role
        # 'views/surgical_team_views.xml', # This was a placeholder
        # Wizards
        # 'wizard/assign_team_wizard_views.xml',
        # Reports
        # 'reports/surgery_report_templates.xml',
        # 'reports/surgery_reports.xml',
    ],
    'installable': True,
    'application': False, # Part of the larger medical application suite
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            # 'medical_surgery/static/src/scss/surgery_dashboard.scss', # Example
        ],
        'web.assets_qweb': [
            # 'medical_surgery/static/src/xml/surgery_templates.xml', # Example
        ],
    },
}
