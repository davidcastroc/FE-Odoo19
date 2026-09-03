# -*- coding: utf-8 -*-

{
    'name': "FE - Costa Rica POS payment method non document",
    'version': "19.0.0.1.0",
    "category": "Point of Sale",
    'author': "SEGU",
    'license': "LGPL-3",
    'summary': "Costa Rica POS payment method non document.",
    'description': "Costa Rica POS payment method non document",
    'depends': ['l10n_cr_invoice_pos'],
    'data': [
        'views/pos_order_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_cr_pos_payment_method_non_document/static/src/**/*',
        ],
    },
}
