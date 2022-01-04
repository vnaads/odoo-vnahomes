# See LICENSE file for full copyright and licensing details.

{
    'name': 'VNA Hotel Management',
    'version': '12.0.1.0.0',
    'author': 'locct',
    'category': 'Hotel Management',
    'depends': ['hotel', 'web', 'account'],
    'license': 'AGPL-3',
    'summary': 'Hotel Management to Manage Folio and Hotel Configuration',
    'demo': ['data/hotel_data.xml'],
    'data': [
            'security/ir.model.access.csv',
            'security/hotel_management_security.xml',
            'views/hotel_contract_type_view.xml',
            'views/hotel_management_views.xml',
            'views/account_invoice_view.xml',
            'views/account_payment_view.xml',
            'wizzard/account_invoice_report_view.xml',
            'wizzard/wizzard_automatic_invoice_view.xml',
            'report/invoice_template_view.xml',
            'report/invoice_template_view_eng_ver.xml',
            'views/action_download_report_template.xml',
            'excel_report/expense_report_view.xml',
            'excel_report/electricity_number_report_view.xml',
            'excel_report/revenue_by_room_report_view.xml'
    ],
    'application': True
}
