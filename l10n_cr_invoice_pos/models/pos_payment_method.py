# -*- coding: utf-8 -*-

from odoo import models, fields, api
# from odoo.addons.l10n_cr_invoice.models.account_move import PAYMENT_METHOD_SELECTION


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    l10n_cr_payment_method_id = fields.Many2one("l10n_cr.payment_method", "Payment Method")
    # l10n_cr_payment_method = fields.Selection(
    #     PAYMENT_METHOD_SELECTION,
    #     string="Payment Method",
    #     default="99",  # Others
    #     help="Costa Rica: payment method to be used.",
    # )
    l10n_cr_country_code = fields.Char(
        related="company_id.account_fiscal_country_id.code",
        string="Country Code (CR)",  # to avoid duplicate string warning ...,
    )
