# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, Command
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError, UserError
from ..hacienda_api import get_exoneration_info
import requests
import json
import logging

_logger = logging.getLogger(__name__)
DESCRIPTION_INSTITUTION_CODE = [
    ('01', 'Ministerio de Hacienda'),
    ('02', 'Ministerio de Relaciones Exteriores y Culto'),
    ('03', 'Ministerio de Agricultura y Ganadería'),
    ('04', 'Ministerio de Economía, Industria y Comercio'),
    ('05', 'Cruz Roja Costarricense'),
    ('06', 'Asociación Obras del Espíritu Santo'),
    ('07', 'Asociación Obras del Espíritu Santo'),
    ('08', 'Federación Cruzada Nacional de protección al Anciano (Fecrunapa)'),
    ('09', 'Escuela de Agricultura de la Región Húmeda (EARTH)'),
    ('10', 'Instituto Centroamericano de Administración de Empresas (INCAE)'),
    ('11', 'Instituto Centroamericano de Administración de Empresas (INCAE)'),
    ('12', 'Autoridad Reguladora de los Servicios Públicos (Aresep)'),
    ('99', 'Otros'),
]


class L10nCrPartnerExoneration(models.Model):
    _name = 'l10n_cr.partner.exoneration'
    _description = 'Partner Exoneration'

    @api.depends('exoneration_number', 'partner_id.name', 'percentage_exoneration')
    def _compute_display_name(self):
        for record in self:
            if record.exoneration_number and record.partner_id:
                record.display_name = f"{record.exoneration_number} - {record.percentage_exoneration}%"
            else:
                record.display_name = record.exoneration_number or 'Nueva Exoneración'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade'
    )
    exoneration_number = fields.Char(
        string='Número de Exoneración',
        required=True,
        help='Número oficial de la exoneración otorgada por la institución'
    )

    institution_name = fields.Selection(DESCRIPTION_INSTITUTION_CODE, 'Nombre de Institucion',
                                        help="NOTA 23: ANEXOS y ESTRCUTURAS")

    exoneration_type_id = fields.Many2one('ce.exoneration.type',
                                          string='Tipo de Exoneración')

    percentage_exoneration = fields.Float(
        string='Porcentaje de Exoneración (%)',
        required=True,
        help='Porcentaje de IVA exonerado (ej: 13 para 13%)'
    )

    date_issue = fields.Datetime(
        string='Fecha de Emisión',
        required=True,
        default=fields.Date.context_today
    )

    date_expiration = fields.Date(
        string='Fecha de Vencimiento',
        required=True
    )

    active = fields.Boolean(
        string='Activa',
        default=True
    )

    description = fields.Text(
        string='Descripción'
    )

    allowed_cabys_line_ids = fields.One2many(comodel_name='l10n_cr.partner.exoneration.cabys.line',
                                             inverse_name='partner_exoneration_id',
                                             string='Líneas de Códigos CABYS',
                                             readonly=False
                                             )

    cabys_count = fields.Integer(
        string='Cantidad de Códigos CABYS',
        compute='_compute_cabys_count',
        store=True
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('allowed_cabys_line_ids')
    def _compute_cabys_count(self):
        for record in self:
            if record.allowed_cabys_line_ids:
                record.cabys_count = len(record.allowed_cabys_line_ids)
            else:
                record.cabys_count = 0

    # === BUSINESS METHODS ===#

    @api.constrains('percentage_exoneration')
    def _check_percentage_exoneration(self):
        for exoneration in self:
            if exoneration.percentage_exoneration < 0.00:
                raise ValidationError(_("The percentage exoneration cannot be negative."))

    def action_reload_cabys(self):
        self.ensure_one()
        if not self.exoneration_number:
            raise UserError(_('Debe especificar el número de exoneración'))

        # Eliminar códigos existentes si los hay
        if self.allowed_cabys_line_ids:
            self.allowed_cabys_line_ids.unlink()
            self.allowed_cabys_line_ids = False

        # Recargar desde Hacienda
        success = self._load_cabys_from_hacienda()
        if not success:
            _logger.warning('No se pudieron cargar los códigos CABYS desde Hacienda')

    def _load_cabys_from_hacienda(self):
        """✅ MEJORADO CON LOGS DETALLADOS DE LA API"""
        if not self.exoneration_number:
            return False

        try:
            # 🔍 LOGS DE DEBUGGING
            _logger.info("=" * 80)
            _logger.info("🌐 DEBUG CONSULTA API HACIENDA")
            _logger.info("=" * 80)
            _logger.info(f"📋 Número de exoneración: {self.exoneration_number}")

            # Obtener URL base de configuración
            # url_base = HACIENDA_URL_EXONERATION
            # if not url_base:
            #     _logger.error('❌ URL base de exoneraciones no configurada')
            #     return False
            #
            # url_base = url_base.strip()
            # if url_base.endswith('/'):
            #     url_base = url_base[:-1]
            #
            # endpoint = f"{url_base}autorizacion={self.exoneration_number}"
            # _logger.info(f"🌐 URL de consulta: {endpoint}")

            headers = {'content-type': 'application/json'}

            # Realizar consulta
            # response = requests.get(endpoint, headers=headers, timeout=10)
            response = get_exoneration_info(self.exoneration_number)
            # _logger.info(f"📡 Status Code: {response.status_code}")
            # _logger.info(f"📏 Content Length: {len(response.content)}")

            if response.status_code in (200, 202) and len(response.content) > 0:
                data = json.loads(response.content.decode('utf-8'))

                # 🔍 LOGS DETALLADOS DE LA RESPUESTA
                _logger.info("📦 DATOS RECIBIDOS DE LA API:")
                _logger.info(f"🆔 Identificación: {data.get('identificacion', 'N/A')}")
                _logger.info(f"📅 Fecha Emisión: {data.get('fechaEmision', 'N/A')}")
                _logger.info(f"📅 Fecha Vencimiento: {data.get('fechaVencimiento', 'N/A')}")
                _logger.info(f"🏛️ Nombre Institución: {data.get('nombreInstitucion', 'N/A')}")

                # ⚠️ PUNTO CRÍTICO: Procesar porcentaje
                if 'porcentajeExoneracion' in data:
                    percentage_from_api = data.get('porcentajeExoneracion')
                    _logger.info(f"📊 PORCENTAJE DESDE API (RAW): {percentage_from_api}")
                    _logger.info(f"📊 Tipo de dato API: {type(percentage_from_api)}")

                    # Convertir a float y dividir entre 100
                    percentage_float = float(percentage_from_api)
                    percentage_decimal = percentage_float / 100

                    _logger.info(f"📊 Porcentaje float: {percentage_float}")
                    _logger.info(f"📊 Porcentaje decimal (final): {percentage_decimal}")

                    # ⚠️ ASIGNACIÓN CRÍTICA
                    self.percentage_exoneration = percentage_decimal
                    _logger.info(f"✅ Porcentaje asignado al campo: {self.percentage_exoneration}")

                # Validar identificación del cliente
                if 'identificacion' in data and self.partner_id and self.partner_id.vat:
                    if self.partner_id.vat != data.get('identificacion'):
                        _logger.warning(
                            f'⚠️ Identificación no coincide: {self.partner_id.vat} vs {data.get("identificacion")}')

                # Procesar fechas
                if 'fechaEmision' in data:
                    self.date_issue = datetime.strptime(str(data.get('fechaEmision'))[:10], '%Y-%m-%d')
                    _logger.info(f"📅 Fecha emisión asignada: {self.date_issue}")

                if 'fechaVencimiento' in data:
                    self.date_expiration = datetime.strptime(str(data.get('fechaVencimiento'))[:10], '%Y-%m-%d')
                    _logger.info(f"📅 Fecha vencimiento asignada: {self.date_expiration}")

                # Procesar institución
                # if 'nombreInstitucion' in data:
                #     institution_name = data.get('nombreInstitucion')
                #     self.institution_name = institution_name
                #     _logger.info(f"🏛️ Institución asignada: {self.institution_name}")

                # Procesar códigos CABYS
                if 'cabys' in data and data['cabys']:
                    cabys_count = len(data['cabys'])
                    _logger.info(f"🏷️ Códigos CABYS encontrados: {cabys_count}")

                    # cabys_lines = []
                    # for cabys_code in data['cabys']:
                    #     cabys_lines.append((0, 0, {
                    #         'cabys_code': cabys_code,
                    #         'description': f'Código {cabys_code}'
                    #     }))
                    #     _logger.info(f"🏷️ Código CABYS: {cabys_code}")

                    if data.get('cabys'):
                        self.allowed_cabys_line_ids = [Command.clear()]
                        aa = [
                            Command.create({'exoneration_code': code, 'cabys_code': code}) for
                            code in data.get('cabys')]
                        for a in aa:
                            p = self.env["product.product"].search([('product_cabys_id.code', '=', a[2]['cabys_code'])], limit=1)
                            if p:
                                a[2]["product_id"] = p.id

                        # self.allowed_cabys_line_ids = [
                        #     Command.create({'exoneration_code': code, 'cabys_code': code}) for
                        #     code in data.get('cabys')]
                        self.allowed_cabys_line_ids = aa

                _logger.info('✅ Códigos CABYS cargados automáticamente')
                _logger.info("=" * 80)
                return True

            else:
                _logger.error(f'❌ API response no válida: Status {response.status_code}')
                return False

        except requests.exceptions.RequestException as e:
            _logger.error(f'❌ Error consultando API de Hacienda: {e}')
            return False
        except Exception as e:
            _logger.error(f'❌ Error procesando respuesta de Hacienda: {e}')
            return False


class L10nCrPartnerExonerationCabysLine(models.Model):
    _name = "l10n_cr.partner.exoneration.cabys.line"
    _description = "Allowed Partner Exoneration CABYS"

    partner_exoneration_id = fields.Many2one(
        comodel_name='l10n_cr.partner.exoneration'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product"
    )
    cabys_code = fields.Char(
        string="CABYS Code",
        size=13
    )
    exoneration_code = fields.Char(
        string="Exoneration Code",
        size=13
    )

    # @api.onchange("product_id")
    # def onchange_product_id(self):
    #     if self.product_id and self.product_id.product_cabys_id:
    #         self.cabys_code = self.product_id.product_cabys_id.code
    #         self.exoneration_code = self.product_id.product_cabys_id.code
