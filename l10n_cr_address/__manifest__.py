# -*- coding: utf-8 -*-

{
    "name": "Topónimos de Costa Rica",
    'countries': ['cr'],
    "summary": "Códigos País para Facturación electrónica Costa Rica.",
    "version": "19.0.1.0.0",
    "author": "SEGU",
    "license": "LGPL-3",
    "category": "Localization",
    "description": "Topónimos de Costa Rica.",
    "depends": ["l10n_cr_invoice"],
    "data": [
        "data/res.country.county.csv",
        "data/res.country.state.csv",
        "data/res.country.district.csv",
        "data/res.country.neighborhood.csv",
        "views/country_codes_views.xml",
        "views/res_partner_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": True,
}
