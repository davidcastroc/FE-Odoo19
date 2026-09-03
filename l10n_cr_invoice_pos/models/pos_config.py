# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    terminal_id = fields.Many2one('ce.terminal', string="Terminal", help="Terminal o Punto de venta.")
    l10n_cr_fiscal_journal = fields.Boolean(
        string='Fiscal POS',
        related='invoice_journal_id.l10n_cr_fiscal_journal',
    )

    def _check_before_creating_new_session(self):
        """Override."""
        super()._check_before_creating_new_session()
        if not self.terminal_id and self.l10n_cr_fiscal_journal:
            raise UserError(_("Not found terminal for this TPV."))

    # def open_ui(self):
    #     """Open the pos interface with config_id as an extra argument.
    #
    #     In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
    #     on opening a session. It is also possible to login to sessions created by other users.
    #
    #     :returns: dict
    #     """
    #     self.ensure_one()
    #     if not self.terminal_id and self.l10n_cr_fiscal_journal:
    #         raise UserError(_("Not found terminal for this TPV."))
    #
    #     return super().open_ui()

    def _create_journal_and_payment_methods(self, cash_ref=None, cash_journal_vals=None):
        """Override."""
        journal, pm_ids = super()._create_journal_and_payment_methods(cash_ref, cash_journal_vals)
        if self.env.company.account_fiscal_country_id.code == "CR":
            for pm in self.env["pos.payment.method"].browse(pm_ids):
                if pm.type == "cash":
                    payment_method_money = self.env["l10n_cr.payment_method"].search([("code", "=", "01")], limit=1)
                    pm.l10n_cr_payment_method_id = payment_method_money
                    # pm.cr_payment_method = "01" # cash
                elif pm.type == "bank":
                    payment_method_bank = self.env["l10n_cr.payment_method"].search([("code", "=", "02")], limit=1)
                    pm.l10n_cr_payment_method_id = payment_method_bank
                    # pm.l10n_cr_payment_method = "02"  # bank deposit
                elif pm.type == "pay_later":
                    payment_method_other = self.env["l10n_cr.payment_method"].search([("code", "=", "99")], limit=1)
                    pm.l10n_cr_payment_method_id = payment_method_other
                    # pm.l10n_cr_payment_method = "99"  # other payment
        return journal, pm_ids
