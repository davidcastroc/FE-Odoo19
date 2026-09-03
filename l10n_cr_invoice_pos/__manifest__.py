# -*- coding: utf-8 -*-

{
    "name": "FE - Costa Rica POS",
    'countries': ['cr'],
    "version": "19.0.0.1.0",
    "author": "SEGU",
    "license": "LGPL-3",
    "category": "Localization",
    "summary": "Facturación electronica Costa Rica POS.",
    "description": "Factura Electronica Costa Rica. Version 4.4",
    "depends": ["point_of_sale", "l10n_cr_invoice"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
        "views/ce_document_view.xml",
        "views/pos_payment_method_views.xml",
        "wizard/l10n_ce_invoice_pos_recreate_wizard_views.xml",
        "report/report_ticket_pos.xml",
        "report/pos_actions.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_cr_invoice_pos/static/src/app/**/*",
            "l10n_cr_invoice_pos/static/src/css/pos.css",
            "l10n_cr_invoice_pos/static/src/css/button.css",
        ],
    },
}
