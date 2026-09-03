# -*- coding: utf-8 -*-

from odoo import models, fields, api


class L10nCrProductCabys(models.Model):
    _name = 'ce.product.cabys'
    _inherit = ['ce.product.cabys', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        if self.env.company.country_id.code == "CR":
            return [('active', '=', True)]
        else:
            return super()._load_pos_data_domain(data)

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'CR':
            params += ['name']
        return params
