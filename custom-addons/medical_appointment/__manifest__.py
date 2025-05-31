{
    'name': 'Medical Appointment Management',
    'version': '18.0.1.0.0',
    'summary': 'Manage medical appointments and patient information',
    'description': 'A module to manage medical appointments, link patients and doctors.',
    'category': 'Services/Medical', # This will be created if it doesn't exist or use existing one
    'author': 'Jules AI',
    'website': 'https://example.com',
    'depends': ['base', 'mail', 'calendar', 'resource'], # Added 'resource'
    'data': [
        'data/ir_module_category_data.xml', # Add this line
        'security/medical_groups.xml',         # Add this line
        'security/ir.model.access.csv',
        'data/medical_appointment_data.xml',
        'views/medical_appointment_views.xml',
        # 'views/res_partner_views.xml', # Not created, views are in medical_appointment_views.xml
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
