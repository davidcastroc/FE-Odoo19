# -*- coding: utf-8 -*-

from odoo.addons.l10n_cr_invoice.hacienda_api import HACIENDA_URL_BASE
from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import requests


class ProductProduct(models.Model):
    _inherit = "product.product"

    def search_code(self):
        self.product_tmpl_id.search_code()

    def search_cabys(self):
        self.product_tmpl_id.search_cabys()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_cabys_id = fields.Many2one('ce.product.cabys', string="Cabys Relacionado")

    def search_code(self):
        if not self.cabys_code:
            raise UserError("¡Debe agregar un código previamente!")

        url_base = HACIENDA_URL_BASE

        if url_base:  # and token :
            # Limpia caracteres en blanco en los extremos
            url_base = url_base.strip()
            if url_base[-1:] == '/':
                url_base = url_base[:-1]
            end_point = url_base + '/fe/cabys?codigo=' + self.cabys_code
            headers = {'content-type': 'application/json'}
            request = requests.get(end_point, headers=headers, timeout=10)
            if request.status_code in (200, 202) and len(request._content) > 0:
                contenido = json.loads(str(request._content, 'utf-8'))
                if len(contenido) < 1:
                    m = "No se encontro ningun item relacionado con el código " + str(self.cabys_code)
                    raise UserError(m)
                else:
                    c = 'Código encontrado en Hacienda:\r\n'
                    for r in contenido:
                        c += "Código: " + str(self.cabys_code) + " = " + str(r['descripcion']) + ' (Tax:' + str(
                            r['impuesto']) + ') \r\n'
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'info',
                            'sticky': True,
                            'message': "%s" % c,
                        }
                    }

    def search_cabys(self):
        url_base = HACIENDA_URL_BASE
        name = self.name
        bus = name.replace('*', '').replace('-', '').replace('.', '').replace(',', '')
        bus_split = bus.split()
        bus_f = []
        bus_s = ''

        for b in bus_split:
            if len(b) > 2:
                bus_f.append(b)
                bus_s += b + ' '

        for l in bus_f:
            if url_base:  # and token :
                # Limpia caracteres en blanco en los extremos
                url_base = url_base.strip()
                if url_base[-1:] == '/':
                    url_base = url_base[:-1]
                end_point = url_base + '/fe/cabys?q=' + bus_s
                headers = {'content-type': 'application/json'}
                # Petición GET a la API
                peticion = requests.get(end_point, headers=headers, timeout=10)
                # Respuesta de la API
                if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content, 'utf-8'))
                    if int(contenido.get('total')) < 1:
                        m = "No se encontro ningun código CAByS para el producto " + str(self.name)
                        raise UserError(m)
                    else:
                        cr = self.env['cabys_relacionados']
                        for r in contenido['cabys']:
                            existe_cabys = cr.search_count([('code', '=', r['codigo'])])
                            if not existe_cabys:
                                cr.create({
                                    'code': r['codigo'],
                                    'name': r['descripcion'],
                                    'tax': r['impuesto'],
                                })
