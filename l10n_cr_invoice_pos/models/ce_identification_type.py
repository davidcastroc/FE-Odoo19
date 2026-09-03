# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class IdentificationType(models.Model):
    _name = "ce.identification.type"
    _inherit = ['ce.identification.type', 'pos.load.mixin']

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
            params += ['name', 'code']
        return params
