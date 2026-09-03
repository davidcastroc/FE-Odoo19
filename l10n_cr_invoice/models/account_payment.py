# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # l10n_cr_payment_method_id = fields.Many2one(related='move_id.l10n_cr_payment_method_id', readonly=False)
    l10n_cr_payment_method_id = fields.Many2one("l10n_cr.payment_method")

    def l10n_cr_receipt_payment_send(self, payment_date, memo):
        move_id = self.move_id
        self.move_id.l10n_cr_receipt_payment_send(payment_date, memo)

    def _get_payment_receipt_report_values(self):
        # EXTENDS 'account'
        values = super()._get_payment_receipt_report_values()

        # cfdi_infos = self.move_id and self.move_id._l10n_mx_edi_get_extra_payment_report_values()
        l10n_cr_infos = self.move_id and self.move_id.country_code == 'CR' and self.l10n_cr_payment_method_id
        if l10n_cr_infos:
            values.update({
                'display_invoices': False,
                'display_payment_method': False,
                # 'cfdi': cfdi_infos,
            })

        return values
