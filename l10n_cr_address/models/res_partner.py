# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re


class ResPartner(models.Model):
    _inherit = "res.partner"

    distrito_id = fields.Many2one("res.country.district", string="Distrito")
    canton_id = fields.Many2one("res.country.county", string="Cantón")
    neighborhood_id = fields.Many2one("res.country.neighborhood", string="Barrios")
    country_id = fields.Many2one(
        default=lambda self: self.env.ref("base.cr")
        if self.env.user.company_id.country_id == self.env.ref("base.cr")
        else False
    )

    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            self.phone = re.sub(r"[^0-9]+", "", self.phone)
            if not self.phone.isdigit():
                alert = {
                    'title': 'Atención',
                    'message': 'Favor no introducir letras, espacios ni guiones en los números telefónicos.'
                }
                return {'value': {'phone': ''}, 'warning': alert}

    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            self.mobile = re.sub(r"[^0-9]+", "", self.mobile)
            if not self.mobile.isdigit():
                alert = {
                    'title': 'Atención',
                    'message': 'Favor no introducir letras, espacios ni guiones en los números telefónicos.'
                }
                return {'value': {'mobile': ''}, 'warning': alert}

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            if not re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', self.email.lower()):
                vals = {'email': False}
                alerta = {
                    'title': 'Atención',
                    'message': 'El correo electrónico no cumple con una estructura válida. ' + str(self.email)
                }
                return {'value': vals, 'warning': alerta}
