# -*- coding: utf-8 -*-
{
    'name': "VNA Restful API",

    'summary': """
        Restful API for Business Management""",

    'description': """
        Restful API for Business Management""",

    'author': "",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'VNA',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'sale',
        'sale_stock',
        'hotel_management'
    ],

    # always loaded
    'data': [

    ],
    # only loaded in demonstration mode
    'installable': True,
    'application': False,
    'auto_install': False,
    'demo': [
        # 'demo/demo.xml',
    ],
}
