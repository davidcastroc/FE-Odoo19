# -*- coding: utf-8 -*-

{
    "name": "Sale Manager Costa Rica",
    "summary": """
        Permite el manejo de las exoneraciones con las posiciones fiscales desde las ordenes de venta.
        Adicional le agrega el campo tipo de descuento en las líneas de los pedidos de ventas.""",
    'countries': ['cr'],
    "version": "19.0.1.0.0",
    "author": "SEGU",
    "license": "LGPL-3",
    "category": "Localization",
    "depends": ["l10n_cr_invoice", "sale_management"],
    "data": [
         "views/sale_order_view.xml",
    ],
}
