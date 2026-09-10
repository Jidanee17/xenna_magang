{
    'name': 'Equipment Loan Tracker',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Equipment borrowing and loan tracking system',
    'description': """
Equipment Loan Tracker
======================

Module untuk mengelola:
- Data peminjam
- Data alat
- Transaksi peminjaman alat
- Status ketersediaan alat
- Status transaksi peminjaman
- Pengembalian alat
""",
    'author': 'Xenna Magang',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'stock', 'account', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/equipment_loan_portal_rule.xml',
        'data/equipment_loan_sequence.xml',
        'data/equipment_loan_stock_data.xml',
        'data/equipment_loan_cron.xml',
        'data/equipment_loan_mail_template.xml',
        'views/borrower_views.xml',
        'views/equipment_loan_views.xml',
        'views/equipment_loan_extension_views.xml',
        'views/equipment_loan_portal_templates.xml',
        'report/equipment_loan_report.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
}
