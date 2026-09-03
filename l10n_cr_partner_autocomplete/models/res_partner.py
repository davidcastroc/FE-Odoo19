# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.l10n_cr_invoice.hacienda_api import HACIENDA_URL_BASE
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.onchange("vat", "country_id")
    def _onchange_l10n_cr_vat_autocomplete(self):
        is_cr_partner = bool(self.country_id == self.env.ref("base.cr"))
        if self.vat and is_cr_partner:
            self.vat = self.vat.strip().replace('-', '')  # Limpia caracteres en blanco en los extremos y los guiones.
            url_base = HACIENDA_URL_BASE
            # Limpia caracteres en blanco en los extremos
            url_base = url_base.strip()
            # Elimina la barra al final de la URL para prevenir error al conectarse
            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + '/fe/ae?identificacion=' + self.vat
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Connection": "keep-alive",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Sec-GPC": "1",
                "Host": "api.hacienda.go.cr"
            }

            # Petición GET a la API
            try:
                request = requests.get(end_point, headers=headers, timeout=10)
            except Exception as e:
                raise UserError(e)

            # Respuesta de la API
            if request.status_code in (200, 202) and len(request._content) > 0:
                content = json.loads(str(request._content, 'utf-8'))
                if 'nombre' in content and 'tipoIdentificacion' in content:
                    # Compatibilidad con FE
                    if 'identification_id' in self._fields:
                        id_type = self.env['ce.identification.type']
                        if 'tipoIdentificacion' in content:
                            tipoIdentificacion = content.get('tipoIdentificacion')
                            if tipoIdentificacion == '01':  # Cedula Fisica
                                self.identification_id = id_type.search([('code', '=', '01')], limit=1).id
                                self.company_type = 'person'
                            elif tipoIdentificacion == '02':  # Cedula Juridica
                                self.identification_id = id_type.search([('code', '=', '02')], limit=1).id
                                self.company_type = 'company'
                            elif tipoIdentificacion == '03':
                                self.identification_id = id_type.search([('code', '=', '03')], limit=1).id
                                self.company_type = 'person'
                            elif tipoIdentificacion == '04':
                                self.identification_id = id_type.search([('code', '=', '04')], limit=1).id
                                self.company_type = 'person'
                            elif tipoIdentificacion == '05':
                                self.identification_id = id_type.search([('code', '=', '05')], limit=1).id
                                self.company_type = 'person'

                    if content.get('nombre') is not None:
                        name = content['nombre']
                        self.name = name
            else:
                output = 'Codigo: ' + str(
                    request.status_code) + ', Mensaje: ' + str(request._content.decode())
                _logger.error(output)
