{
    'name': 'Medical Staff Schedule Management',
    'version': '18.0.1.0.0',
    'summary': 'Manage schedules and availability for medical staff',
    'description': 'Allows defining working hours, shifts, and exceptions for doctors.',
    'category': 'Services/Medical',
    'author': 'Jules AI',
    'website': 'https://example.com',
    'depends': ['medical_appointment', 'resource'], # Added 'resource' for working time concepts
    'data': [
        'security/ir.model.access.csv',
        'views/doctor_schedule_views.xml',
        'data/medical_schedule_data.xml',
    ],
    'installable': True,
    'application': False, # This is not a standalone application, but an addon
    'auto_install': False,
}
