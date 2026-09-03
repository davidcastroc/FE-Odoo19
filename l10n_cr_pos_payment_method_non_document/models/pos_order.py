# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    non_document = fields.Boolean(
        string="Non Document"
    )

    def create_from_non_document(self):
        if not self.document_id:
            terminal_id = self.session_id.config_id.terminal_id
            if not terminal_id:
                raise UserError(_("Not found terminal for this TPV."))

            # if self.refunded_orders_count:
            #     raise UserError(_("Only apply to FE or NC."))

            voucher_type_code = '01' if self.to_invoice else '04'
            return self.l10n_cr_create_document(terminal_id, code=voucher_type_code)

        return False

    def l10n_cr_can_create_document(self, order):
        res = super().l10n_cr_can_create_document(order)
        return res and not order.non_document
