# -*- coding: utf-8 -*-

from odoo import fields, models


class UoM(models.Model):
    _inherit = "uom.uom"

    # Código de unidad utilizado por Hacienda Costa Rica.
    code = fields.Char()
