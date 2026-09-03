# -*- coding: utf-8 -*-

{
    "name": "CABYS para Costa Rica",
    'countries': ['cr'],
    "summary": "Datos de CABYS para Comprobantes Electronicos de Costa Rica.",
    "version": "19.0.1.0.0",
    "author": "SEGU",
    "license": "LGPL-3",
    "category": "Localization",
    "depends": ["l10n_cr_invoice"],
    "data": [
         "data/ce.product.cabys.csv",
         "security/ir.model.access.csv",
         "views/product_view.xml",
         "views/l10n_cr_product_cabys_views.xml",
         "views/res_config_settings_view.xml",
     ],
    "auto_install": True,
}
