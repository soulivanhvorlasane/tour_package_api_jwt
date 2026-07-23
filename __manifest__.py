{
    'name': 'Tour Package API JWT',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'JWT API Authentication',
    'description': """
API Auth Token
==============
Provides secure JWT-based authentication and protected API endpoints.
Integrates with the tour_package module to expose user profile, package bookings, and booking calendar.
    """,
    'depends': ['base', 'web', 'tour_package'],
    'external_dependencies': {
        'python': ['PyJWT'],
    },
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
