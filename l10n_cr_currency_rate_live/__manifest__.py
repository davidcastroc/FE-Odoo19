# -*- coding: utf-8 -*-

{
    'name': "Tipo de Cambio BCCR",
    'countries': ['cr'],
    "version": "19.0.1.0.0",
    'author': "SEGU",
    'license': "LGPL-3",
    'category': "Account",
    "summary": "Tipo de Cambio del BCCR.",
    'description': "Tipo de Cambio del Banco Central de Costa Rica ₡/$/€",
    'depends': ['account', 'l10n_cr'],
    'data': [
        "data/ir_cron_data.xml",
        "data/ir_config_parameter_data.xml",
        "views/res_config_settings_views.xml",
    ]
}
