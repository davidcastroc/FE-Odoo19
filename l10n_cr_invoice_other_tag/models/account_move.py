# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_cr_salesman_number = fields.Char(string="Salesman Number", help="Salesman number associated with the invoice.")
    l10n_cr_order_number = fields.Char(string="Order Number", help="Order number associated with the invoice.")
    l10n_cr_pv_number = fields.Char(string="PV Number", help="Point of Sales number associated with the invoice.")
    l10n_cr_delivery_date = fields.Date(string="Delivery Date", help="Date of delivery associated with the invoice.")
    l10n_cr_reception_number = fields.Char(string="Reception Number", help="Reception number associated with the invoice.")
