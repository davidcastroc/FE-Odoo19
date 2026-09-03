# -*- coding: utf-8 -*-

from odoo import models, fields, _


class AccountMove(models.Model):
    _inherit = "account.move"

    supplier_economic_activity_id = fields.Many2one('ce.economic.activity', string="Supplier Economic Activity",
                                                    ondelete="restrict")
