# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command


class L10nCrInvoicePosRecreateWizard(models.Model):
    _name = 'l10n_cr_invoice_pos.recreate.wizard'
    _description = "Recreate POS Invoice Wizard"

    pos_order_ids = fields.Many2many(comodel_name='pos.order')

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)

        if 'pos_order_ids' in results:
            source_orders = self.env['pos.order'].browse(results['pos_order_ids'][0][2])
            invoices = source_orders._l10n_cr_check_order_for_recreate()
            results['pos_order_ids'] = [Command.set(invoices.ids)]

        return results

    def action_create_global_invoice(self):
        self.ensure_one()
        self.pos_order_ids._l10n_cr_invoice_pos_recreate_try()
