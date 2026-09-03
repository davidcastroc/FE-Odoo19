# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    invoice_import_count = fields.Integer(compute="_compute_count_invoice_imported")

    def _compute_count_invoice_imported(self):
        count = self.env["account.move"].search_count([('purchase_order_id', '=', self.id)])
        self.invoice_import_count = count

    def action_view_document_reference(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported Invoice'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('purchase_order_id', '=', self.id)],
        }
