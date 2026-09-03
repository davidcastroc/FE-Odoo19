{
    "name": "Facturas de proveedor Extract - Costa Rica",
    'countries': ['cr'],
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": """
        Extract data from invoice scans to fill them automatically.
     """,
    "author": "NIMETRIX",
    "depends": ["l10n_cr_invoice_receptor", "account_invoice_extract"],
    "data": [
        "data/ir_cron_data.xml",
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
    ],
    "license": "LGPL-3",
}
