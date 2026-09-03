# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_cr_payment_method_id = fields.Many2one(
        comodel_name='l10n_cr.payment_method',
        string="Payment Way",
        readonly=False, store=True,
        compute='_compute_cr_payment_method_id',
        help="Indicates the way the payment was/will be received, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc.")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('journal_id')
    def _compute_cr_payment_method_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.l10n_cr_payment_method_id = wizard.line_ids.move_id.l10n_cr_payment_method_id[:1]
            else:
                wizard.l10n_cr_payment_method_id = False

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payments(self):
        payment = super()._create_payments()
        if self.line_ids.move_id.payment_term_type_id.code == "08":
            # Venta a crédito en IVA
            # payment.l10n_cr_receipt_payment_send(payment_date=self.payment_date, memo=self.communication)
            move_id = self.line_ids.move_id
            move_id.l10n_cr_receipt_payment_send(condition_code="09", payment_date=self.payment_date, memo=payment.name)
            # move_id.l10n_cr_receipt_payment_send(payment_date=self.payment_date, memo=self.communication)
        if self.line_ids.move_id.payment_term_type_id.code == "10":
            # Venta a crédito en IVA
            # payment.l10n_cr_receipt_payment_send(payment_date=self.payment_date, memo=self.communication)
            move_id = self.line_ids.move_id
            move_id.l10n_cr_receipt_payment_send(condition_code="11", payment_date=self.payment_date, memo=payment.name)
            # move_id.l10n_cr_receipt_payment_send(payment_date=self.payment_date, memo=self.communication)

        return payment

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['l10n_cr_payment_method_id'] = self.l10n_cr_payment_method_id.id
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals['l10n_cr_payment_method_id'] = self.l10n_cr_payment_method_id.id
        return payment_vals
