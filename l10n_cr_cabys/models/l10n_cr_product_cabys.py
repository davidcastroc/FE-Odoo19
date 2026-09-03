# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductCabys(models.Model):
    _name = "ce.product.cabys"
    _description = "Catalog of products and services CABYS"
    _sql_constraints = [('ce_code_uniq', 'unique (code)', 'Ya existe un registro con el mismo código.')]

    code = fields.Char('Código', required=True, size=13)
    name = fields.Char('Descripción', required=True)
    tax = fields.Integer('Impuesto')
    active = fields.Boolean(default=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"({rec.code}) {rec.name}"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ search in name, code and category"""
        args = args or []
        # search in name and code
        domain = args + ['|', ('name', operator, name), ('code', operator, name)]
        product_cabys = self.search_fetch(
            domain, ['display_name'], limit=limit,
        )
        return [(sol.id, sol.display_name) for sol in product_cabys]
