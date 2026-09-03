# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _prepare_document_additional_values(self):
        res = super()._prepare_document_additional_values()
        if self.pos_order_ids:
            res['order_id'] = self.pos_order_ids[0].id

        return res
