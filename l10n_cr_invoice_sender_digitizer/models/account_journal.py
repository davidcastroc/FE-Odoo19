# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from odoo.addons.l10n_cr_invoice.models import FE
from odoo.addons.l10n_cr_invoice.models import NC
from odoo.addons.l10n_cr_invoice.models import ND
from odoo.addons.l10n_cr_invoice.hacienda_api import HACIENDA_VERSION, get_economic_activities
from . import api_import_mail
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import SUPERUSER_ID
import xml.etree.ElementTree as ET
import tempfile
import os
import subprocess
import json
import logging

_logger = logging.getLogger(__name__)

VOUCHER_TYPE_MAP = {
    'FacturaElectronica': '01',
    'NotaDebitoElectronica': '02',
    'NotaCreditoElectronica': '03',
    'TiqueteElectronico': '04',
}


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # ============================================================
    # HELPERS (NUEVO) - para no volver a explotar por campos/métodos
    # ============================================================
    def _safe_call(self, obj, method_name, default=False):
        """Llama obj.method_name() si existe, si no devuelve default."""
        try:
            if obj and hasattr(obj, method_name):
                return getattr(obj, method_name)()
        except Exception:
            return default
        return default

    def _filter_existing_fields(self, model_name, vals):
        """Elimina keys que no existan en el modelo (ej: fax en res.partner)."""
        Model = self.env[model_name]
        return {k: v for k, v in vals.items() if k in Model._fields}

    def _create_document_from_attachment(self, attachment_ids):
        """ Create the invoices from files."""
        if not self:
            self = self.env['account.journal'].browse(self._context.get("default_journal_id"))
        move_type = self._context.get("default_move_type", "entry")
        if not self:
            if move_type in self.env['account.move'].get_sale_types(include_receipts=True):
                journal_type = "sale"
            elif move_type in self.env['account.move'].get_purchase_types(include_receipts=True):
                journal_type = "purchase"
            else:
                raise UserError(_("The journal in which to upload the invoice is not specified."))

            self = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', journal_type),
                ('l10n_cr_fiscal_journal', '=', False),
            ], limit=1)

        attachments = self.env['ir.attachment'].sudo().browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        if not self:
            raise UserError(_("No journal found. Please must be create a jornal %s not fiscal.") % journal_type)

        if move_type not in ["out_invoice", "out_refund"]:
            raise UserError("Esta accion solo es permitida para diarios de compra-reembolso.")

        ce_version = HACIENDA_VERSION

        all_invoices = self.env['account.move']
        for attachment in attachments:
            if attachment.mimetype not in ['application/zip']:
                raise UserError(_("The uploaded file is not supported. Bust be ZIP file."))

            attachment_xml = api_import_mail.l10n_cr_get_attachment_zip(attachment.raw)

            try:
                parser = ET.XMLParser(encoding="utf-8")
                root = ET.fromstring(attachment_xml, parser=parser)
                tipo_xml = root.tag.split('}')[-1]
                if not root.tag.split('}')[0].find(f'/v{ce_version}/') >= 0:
                    raise ValidationError("Version no soportada")
            except Exception as e:
                raise ValidationError(e)

            if tipo_xml is None:
                raise ValidationError(_("Could not find document type."))

            file = tempfile.NamedTemporaryFile(delete=False)
            file.write(attachment_xml)
            file.close()
            filename = file.name

            if tipo_xml == 'FacturaElectronica':
                docu = FE.parseString(attachment_xml, silence=True)
                tipo = VOUCHER_TYPE_MAP[tipo_xml]

            elif tipo_xml == 'NotaCreditoElectronica':
                docu = NC.parseString(attachment_xml, silence=True)
                tipo = VOUCHER_TYPE_MAP[tipo_xml]

            elif tipo_xml == 'NotaDebitoElectronica':
                docu = ND.parseString(attachment_xml, silence=True)
                tipo = VOUCHER_TYPE_MAP[tipo_xml]

            else:
                _logger.info("Tipo de comprobante desconocido: %s", tipo_xml)
                subprocess.call(['rm', '-f', filename])
                continue

            subprocess.call(['rm', '-f', filename])

            if move_type == "out_invoice":
                company_id = self.company_id
                sender = docu.get_Emisor()
                if sender:
                    if sender.get_Identificacion().get_Numero() != company_id.vat:
                        raise ValidationError(
                            "El archivo esta dirigido a la identificacion: {} que no coincide con la identificacion de la compañia {}".format(
                                sender.get_Identificacion().get_Numero(), self.env.company.vat))

                receiver = docu.get_Receptor()
                identification_type = receiver.get_Identificacion().get_Tipo()
                ident_number = receiver.get_Identificacion().get_Numero()
                tin_type = self.env['ce.identification.type'].search([('code', '=', identification_type)])

                if not tin_type:
                    raise ValidationError(_("Identification Type: " + identification_type + " not recognized"))

                domain = [('vat', '=', ident_number), ('identification_id', '=', tin_type.id)]
                partner_id = self.env['res.partner'].search(domain, limit=1)

                if not partner_id:
                    partner_id = self.l10n_cr_create_partner_from_doc(receiver)

            if move_type == "out_refund":
                sender = docu.get_Emisor()
                identification_type = sender.get_Identificacion().get_Tipo()
                ident_number = sender.get_Identificacion().get_Numero()
                tin_type = self.env['ce.identification.type'].search([('code', '=', identification_type)])

                if not tin_type:
                    raise ValidationError(_("Identification Type: " + identification_type + " not recognized"))

                domain = [('vat', '=', ident_number), ('identification_id', '=', tin_type.id)]
                partner_id = self.env['res.partner'].search(domain, limit=1)

            invoice = self.l10n_cr_create_invoice(docu, partner_id, tipo, tipo_xml)
            all_invoices |= invoice
            invoice.with_context(
                account_predictive_bills_disable_prediction=True,
                no_new_invoice=True,
            ).message_post(attachment_ids=attachment.ids)
            attachment.sudo().write({'res_model': 'account.move', 'res_id': invoice.id})

        return all_invoices

    @api.model
    def l10n_cr_create_partner_from_doc(self, partner):
        cedula_type = partner.get_Identificacion().get_Tipo()
        cedula = partner.get_Identificacion().get_Numero()
        tin_type = self.env['ce.identification.type'].search([('code', '=', cedula_type)])
        country_id = self.env['res.country'].search([('phone_code', '=', '506')])

        ubicacion = partner.get_Ubicacion()
        provincia_txt = ubicacion.get_Provincia() if ubicacion else None
        canton_txt = ubicacion.get_Canton() if ubicacion else None
        distrito_txt = ubicacion.get_Distrito() if ubicacion else None
        barrio_txt = ubicacion.get_Barrio() if ubicacion else None
        otras_senas = ubicacion.get_OtrasSenas() if ubicacion else None

        state_id = None
        canton_id = None
        distrito_id = None
        barrio_id = None

        if country_id:
            domain = [('code', '=', provincia_txt), ('country_id', '=', country_id.id)]
            state_id = self.env['res.country.state'].search(domain)

        if state_id and canton_txt:
            domain = [('code', '=', canton_txt), ('state_id', '=', state_id.id)]
            canton_id = self.env['res.country.county'].search(domain)

        if canton_id and distrito_txt:
            domain = [('code', '=', distrito_txt), ('county_id', '=', canton_id.id)]
            distrito_id = self.env['res.country.district'].search(domain)

        if distrito_id and barrio_txt:
            domain = [('code', '=', barrio_txt), ('district_id', '=', distrito_id.id)]
            barrio_id = self.env['res.country.neighborhood'].search(domain)

        partner_vals = {
            'name': partner.Nombre.encode('utf-8'),
            'commercial_name': partner.get_NombreComercial().encode('utf-8') if partner.get_NombreComercial() else False,
            'identification_id': tin_type.id if tin_type else False,
            'vat': cedula,
            'phone': str(partner.get_Telefono().get_NumTelefono()) if partner.get_Telefono() else '',
            'email': partner.get_CorreoElectronico(),
            'street': otras_senas if otras_senas else '',
            'country_id': country_id.id if country_id else None,
            'state_id': state_id.id if state_id else None,
            'canton_id': canton_id.id if canton_id else None,
            'distrito_id': distrito_id.id if distrito_id else None,
            'neighborhood_id': barrio_id.id if barrio_id else None,
            'is_company': True if cedula_type == '02' else False
        }

        partner_vals = self._filter_existing_fields('res.partner', partner_vals)
        new_partner = self.env['res.partner'].create(partner_vals)
        return new_partner

    @api.model
    def l10n_cr_create_get_product(self, lineadetalle, partner_id, company_id, currency_id):
        products = []
        ProductProduct = self.env['product.product']
        codigo_cabys = lineadetalle.get_Codigo()
        product_name = lineadetalle.get_Detalle().strip()
        product_code = ""
        barcode = ""
        default_code = ""

        args = [('partner_id', '=', partner_id.id), '|', ('product_name', '=', product_name)]

        for codigo_comercial in lineadetalle.get_CodigoComercial():
            codigo_tipo = codigo_comercial.get_Tipo()
            codigo_value = codigo_comercial.get_Codigo().strip()

            if codigo_tipo == '01':
                product_code = codigo_value
                args.append(('product_code', '=', product_code))
            elif codigo_tipo == '02':
                default_code = codigo_value
            elif codigo_tipo == '03':
                barcode = codigo_value
            elif codigo_tipo == '04' and not default_code:
                default_code = codigo_value
            elif codigo_tipo == '99' and not default_code:
                default_code = codigo_value

        if not product_code:
            del (args[1])

        if not products and partner_id:
            suppliers = self.env['product.supplierinfo'].search(args)
            if suppliers:
                products = ProductProduct.search([('seller_ids', 'in', suppliers.ids)], limit=1)

        if not products and barcode:
            products = ProductProduct.search([('barcode', '=', barcode)], limit=1)

        if not products and default_code:
            products = ProductProduct.search([('default_code', '=', default_code)], limit=1)

        if not products and product_name:
            products = ProductProduct.search([('name', '=', product_name)], limit=1)
            if not products:
                products = ProductProduct.search([('name', 'ilike', product_name)], limit=1)

        if not products:
            price_unit = lineadetalle.get_PrecioUnitario()
            journal_type = self.type

            vals = {
                'name': product_name,
                'detailed_type': 'product',
                'cabys_code': codigo_cabys,
                'company_id': company_id.id,
                'sale_ok': False,
            }
            if journal_type == "sale":
                vals['list_price'] = price_unit
            if journal_type == "purchase":
                vals['standard_price'] = price_unit

            if codigo_cabys and len(codigo_cabys) == 13:
                cabys = self.env['ce.product.cabys'].search([('code', '=', codigo_cabys)], limit=1)
                if cabys:
                    vals['product_cabys_id'] = cabys.id

            uom_code_id = self.env['uom.uom'].search([('code', '=', lineadetalle.get_UnidadMedida())], limit=1)
            if not uom_code_id:
                uom_code_id = self.env['uom.uom'].search([('code', '=', 'Unid')], limit=1)

            vals['uom_id'] = uom_code_id.id
            vals['uom_po_id'] = uom_code_id.id

            if barcode:
                vals['barcode'] = barcode
                vals['default_code'] = barcode

            impuestos = lineadetalle.get_Impuesto() or []
            supplier_taxes_id = []
            for impl in impuestos:
                imp = self.env['account.tax'].search([
                    ('code_cr', '=', impl.get_Codigo()),
                    ('active', '=', True),
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', impl.get_Tarifa()),
                    ('company_id', '=', company_id.id)
                ], limit=1)

                if imp:
                    supplier_taxes_id.append(imp.id)

            if supplier_taxes_id:
                vals['supplier_taxes_id'] = [(6, 0, supplier_taxes_id)]

            supplierinfo = {
                'partner_id': partner_id.id,
                'product_name': product_name,
                'price': price_unit,
                'currency_id': currency_id.id,
                'min_qty': 1,
            }
            if product_code:
                supplierinfo['product_code'] = product_code

            vals['seller_ids'] = [(0, 0, supplierinfo)]
            products = ProductProduct.create(vals)

        return products

    def l10n_cr_get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    def l10n_cr_create_invoice(self, docu, partner_id, tipo, voucher_type_txt, **kwargs):
        invoice_vals = self._l10n_cr_prepare_invoice_model(docu, partner_id, tipo, voucher_type_txt)
        invoice_vals['journal_id'] = self.id
        invoice_vals.update(kwargs)
        invoice_id = self.env['account.move'].create(invoice_vals)
        return invoice_id

    def _l10n_cr_prepare_invoice_model(self, docu, partner_id, tipo, voucher_type_txt):
        move_type = self._context.get("default_move_type", "in_invoice")
        company_id = self.company_id
        invoice_type = move_type
        if tipo == '03':
            invoice_type = 'in_refund'

        # ======================================================
        # FIX 2: Plazo/MedioPago/CondicionVenta con fallback seguro
        # ======================================================
        plazo_credito = self._safe_call(docu, 'get_PlazoCredito', default=False)
        if plazo_credito is False:
            plazo_credito = None

        medios_pago = self._safe_call(docu, 'get_MedioPago', default=[]) or []
        if isinstance(medios_pago, str):
            medios_pago = [medios_pago]

        medio_pago = ''
        if '01' in medios_pago:
            medio_pago = 'Contado'
        elif '02' in medios_pago:
            medio_pago = 'Crédito'
        elif '03' in medios_pago:
            medio_pago = 'Consignación'
        elif '04' in medios_pago:
            medio_pago = 'Apartado'
        elif '05' in medios_pago:
            medio_pago = 'Arrendamiento con opción de compra'
        elif '06' in medios_pago:
            medio_pago = 'Arrendamiento en función financiera'
        elif '99' in medios_pago:
            medio_pago = 'Otros'

        fpos = None
        voucher_type_code = VOUCHER_TYPE_MAP.get(voucher_type_txt)
        if not voucher_type_code:
            raise ValidationError(_("Voucher Type not found: " + str(voucher_type_txt)))

        issue_date = docu.get_FechaEmision()
        condicion_venta = self._safe_call(docu, 'get_CondicionVenta', default=False)

        # ======================================================
        # FIX 3: Código de actividad v4.4 (Emisor/Receptor) + fallback
        # ======================================================
        EconomicActivity = self.env['ce.economic.activity']

        codigo_actividad = (
            self._safe_call(docu, 'get_CodigoActividad', default=False)
            or self._safe_call(docu, 'get_CodigoActividadEmisor', default=False)
            or self._safe_call(docu, 'get_CodigoActividadReceptor', default=False)
        )

        if not codigo_actividad:
            raise ValidationError(_("No se encontró Código de Actividad en el XML (ni Emisor ni Receptor)."))

        economic_activity_id = EconomicActivity.search([('code', '=', codigo_actividad)], limit=1)

        if not economic_activity_id:
            response, vals = get_economic_activities(partner_id.vat)
            if response.status_code in (200, 202) and len(response._content) > 0:
                content = json.loads(str(response._content, 'utf-8'))
                if content.get('actividades'):
                    actividades = content['actividades']
                    if len(actividades) < 1:
                        raise ValidationError(
                            "No se encontraron actividades económicas para la identificación: " + str(partner_id.vat)
                        )

                    for a in actividades:
                        if a['codigo'] == codigo_actividad:
                            activity = EconomicActivity.create({
                                'code': a['codigo'],
                                'name': a['descripcion'],
                            })
                            economic_activity_id = activity
                            break

            if not economic_activity_id:
                raise ValidationError(_("Economic Activity not found: " + str(codigo_actividad)))

        if tipo == '01':
            voucher_type_id = self.env.ref('l10n_cr_invoice.voucher_01')
        elif tipo == '03':
            voucher_type_id = self.env.ref('l10n_cr_invoice.voucher_03')
        else:
            voucher_type_id = self.env.ref('l10n_cr_invoice.voucher_02')

        invoice_vals = {
            'move_type': invoice_type,
            'ref': docu.get_NumeroConsecutivo() if invoice_type in ('in_invoice', 'in_refund') else False,
            'l10n_cr_document_number': docu.get_Clave(),
            'partner_id': partner_id.id,
            'invoice_date': fields.Date.to_string(issue_date),
            'company_id': company_id.id,
            'narration': 'Plazo de credito %s dias. Medio de pago: %s ' % (plazo_credito, medio_pago),
            'xml_amount_tax': float(docu.get_ResumenFactura().get_TotalImpuesto()),
            'xml_amount_total': float(docu.get_ResumenFactura().get_TotalComprobante()),
            'l10n_cr_supplier_economic_activity_id': economic_activity_id.id,
            'voucher_type_id': voucher_type_id.id,
        }

        if condicion_venta == "02":
            try:
                credit_term = int(plazo_credito or 0)
            except ValueError:
                credit_term = 0

            invoice_date_due = issue_date + relativedelta(days=credit_term)
            invoice_vals.update({"invoice_date_due": invoice_date_due})
        else:
            payment_term_id = self.env['account.payment.term'].search(
                [('payment_type_id.code', '=', condicion_venta)], limit=1)
            invoice_vals.update({"invoice_payment_term_id": payment_term_id.id})

        if (docu.get_ResumenFactura().get_CodigoTipoMoneda()
                and docu.get_ResumenFactura().get_CodigoTipoMoneda().get_CodigoMoneda() != 'CRC'):
            self._l10n_cr_gen_otra_mondeda(docu, invoice_vals)

        invoice_lines = []
        fiscal_position = False
        service_details = docu.get_DetalleServicio()
        other_charges = docu.get_OtrosCargos()

        for l in service_details.get_LineaDetalle():
            product_name = l.get_Detalle()

            line_taxes = []
            if l.get_Impuesto():
                for i in l.get_Impuesto():
                    if i.get_Exoneracion():
                        exoneration = i.get_Exoneracion()
                        exo = self.env["ce.exoneration"].search(
                            [('document_number', '=', exoneration.get_NumeroDocumento())], limit=1)
                        if not exo:
                            raise ValidationError(_(
                                f"Exoneration not found in system: {exoneration.get_NumeroDocumento()}"
                            ))

                        fpos = self.env["account.fiscal.position"].search([
                            ('exoneration_authorization', '=', True),
                            ('exoneration_id', '=', exo.id)
                        ], limit=1)
                        if not fpos:
                            raise ValidationError(_(
                                f"Fiscal Position with exoneration not found in system: {exoneration.get_NumeroDocumento()}"
                            ))

                        fiscal_position = fpos

                    codigo_cr = i.get_Codigo()

                    # ======================================================
                    # FIX 4: CodigoTarifa en v4.4 => CodigoTarifaIVA
                    # ======================================================
                    tarifa_cr = (
                        self._safe_call(i, 'get_CodigoTarifa', default=False)
                        or self._safe_call(i, 'get_CodigoTarifaIVA', default=False)
                        or None
                    )

                    if i.get_Exoneracion() and fpos:
                        for tax_map in fpos.tax_ids:
                            if tax_map.tax_dest_id:
                                codigo_cr = tax_map.tax_dest_id.code_cr
                                tarifa_cr = tax_map.tax_dest_id.iva_tax_rate

                    search_params = [
                        ('code_cr', '=', codigo_cr),
                        ('type_tax_use', '=', 'sale' if move_type == 'out_invoice' else 'purchase'),
                        ('company_id', '=', company_id.id),
                    ]
                    if tarifa_cr:
                        search_params.append(('iva_tax_rate', '=', tarifa_cr))

                    tax_id = self.env['account.tax'].search(search_params, limit=1)

                    if not tax_id:
                        journal_type = 'sale' if invoice_type == 'out_invoice' else 'purchase'
                        raise ValidationError(_(
                            f"Tax not found in system {journal_type}: {i.get_Codigo()} "
                            f"with amount: {str(i.get_Tarifa())} in company active."
                        ))

                    line_taxes.append(tax_id.id)
            else:
                search_params = [
                    ('code_cr', '=', '01'),
                    ('iva_tax_rate', '=', '01'),
                    ('active', '=', True),
                    ('type_tax_use', '=', 'sale' if move_type == 'out_invoice' else 'purchase'),
                    ('company_id', '=', company_id.id),
                ]
                tax_id = self.env['account.tax'].search(search_params, limit=1)
                if tax_id:
                    line_taxes.append(tax_id.id)

            inv_line_values = {
                'name': product_name,
                'price_unit': l.get_PrecioUnitario(),
                'quantity': l.get_Cantidad(),
                'tax_ids': [Command.set(line_taxes)],
                'account_id': self.default_account_id.id,
            }

            total_amount_discount = 0.0
            for discount in l.get_Descuento():
                total_amount_discount += float(discount.get_MontoDescuento())

            # ======================================================
            # FIX DESCUENTO 100%: permitir importación de compras
            # - Si descuento >= subtotal bruto (qty*unit), se vuelve línea bonificada:
            #   price_unit=0, sin impuestos y sin %discount.
            # ======================================================
            if total_amount_discount > 0:
                line_gross = float(l.get_Cantidad()) * float(l.get_PrecioUnitario())
                eps = 0.00001  # tolerancia por redondeos

                # Si el descuento cubre TODO (o casi todo)
                if total_amount_discount >= (line_gross - eps):
                    inv_line_values.update({
                        'price_unit': 0.0,
                        'tax_ids': [Command.set([])],
                    })
                    inv_line_values['name'] = (
                        f"{product_name} (Bonificación 100% según XML. "
                        f"Original: {line_gross:.5f}, Descuento: {total_amount_discount:.5f})"
                    )
                else:
                    # Descuento parcial: convertir a porcentaje para Odoo
                    base = float(l.get_MontoTotal()) if l.get_MontoTotal() else line_gross
                    discount_percent = round((total_amount_discount / base) * 100, 2) if base else 0.0
                    if discount_percent > 0:
                        inv_line_values['discount'] = discount_percent

            invoice_lines.append([0, False, inv_line_values])

        for charge in other_charges:
            inv_line_values = {
                'name': charge.get_Detalle(),
                'price_unit': float(charge.get_MontoCargo()),
                'quantity': 1,
            }
            invoice_lines.append([0, False, inv_line_values])

        if fiscal_position:
            invoice_vals['fiscal_position_id'] = fiscal_position.id

        invoice_vals['invoice_line_ids'] = invoice_lines
        return invoice_vals

    @api.model
    def _l10n_cr_gen_otra_mondeda(self, docu, invoice_vals):
        currency_code = docu.get_ResumenFactura().get_CodigoTipoMoneda().get_CodigoMoneda()
        currency_rate = docu.get_ResumenFactura().get_CodigoTipoMoneda().get_TipoCambio()
        ResCurrency = self.env['res.currency'].sudo()
        currency_id = ResCurrency.with_context(active_test=False).search([('name', '=', currency_code)], limit=1)
        if not currency_id:
            _logger.info("Tipo de moneda no encontrada.")
            return False

        if not currency_id.active:
            currency_id.active = True

        invoice_vals["currency_id"] = currency_id.id
        if currency_id and currency_id.active:
            invoice_vals["currency_rate"] = currency_rate

        return currency_id

    # @api.model
    # def parse_xsd(self, xml_file, xsd_file):
    #     result = {}
    #     try:
    #         xml_doc = etree.parse(xml_file)
    #         xmlschema = etree.XMLSchema(etree.parse(xsd_file))
    #         is_valid = xmlschema.validate(xml_doc)
    #
    #         validation_errors = []
    #         if not is_valid:
    #             for error in xmlschema.error_log:
    #                 if "Missing child element(s)" not in error.message:
    #                     validation_errors.append(f"Error: {error.message} (línea {error.line})")
    #
    #         if validation_errors:
    #             raise etree.DocumentInvalid(", ".join(validation_errors))
    #
    #         result["message"] = "El documento XML ha sido validado correctamente con respecto al esquema XSD."
    #         result["valid"] = True
    #
    #     except etree.XMLSyntaxError as e:
    #         result["message"] = f"Error de sintaxis XML: {str(e)}"
    #         result["valid"] = False
    #
    #     except etree.DocumentInvalid as e:
    #         result["message"] = f"Error de validación: {str(e)}"
    #         result["valid"] = False
    #
    #     except Exception as e:
    #         result["message"] = f"Error inesperado: {str(e)}"
    #         result["valid"] = False
    #
    #     return result
