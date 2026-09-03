# -*- coding: utf-8 -*-
{
    "name": "Costa Rica - Consulta de Contribuyentes MH",
    "summary": "Consulta datos de contribuyentes en el Ministerio de Hacienda desde Contactos",
    "version": "19.0.1.0.0",
    "category": "Localization/Costa Rica",
    "author": "Castro Li",
    "license": "LGPL-3",
    "depends": ["base", "contacts"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "wizard/res_partner_mh_wizard_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
