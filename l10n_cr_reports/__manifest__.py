# -*- coding: utf-8 -*-

{
    "name": "Declaraciones IVA",
    "summary": """
        Este módulo extiende las funcionalidades del l10n_cr_invoice,
        integrando los reportes de declaraciones fiscales""",
    "author": "SEGU",
    "license": "LGPL-3",
    "category": "Accounting",
    "version": "19.0.1.0.0",
    "depends": ["l10n_cr_invoice"],
    "data": [
        "security/ir.model.access.csv",
        # "reports/account_report_iva_analysis_views.xml",
        "reports/l10n_cr_report.xml",
        "reports/report_iva_details.xml",
        "wizard/report_iva_details_wizard.xml",
    ],
    "assets": {
        'web.assets_backend': [
            'l10n_cr_reports/static/src/**/*',
        ],
    },
}
