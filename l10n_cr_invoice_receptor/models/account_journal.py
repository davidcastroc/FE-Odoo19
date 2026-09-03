# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from .Invoice import Invoice, InvoiceLine
from odoo.addons.l10n_cr_invoice.models import FE
from odoo.addons.l10n_cr_invoice.models import NC
from odoo.addons.l10n_cr_invoice.models import ND
from .FE43 import extractor_43
from odoo.addons.l10n_cr_invoice.hacienda_api import HACIENDA_VERSION, get_economic_activities
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import SUPERUSER_ID
import xml.etree.ElementTree as ET
import tempfile
import subprocess
import json
import logging
_logger = logging.getLogger(__name__)

L10N_CR_VOUCHER_TYPE_MAP = {
    'FacturaElectronica': '01',
    'NotaDebitoElectronica': '02',
    'NotaCreditoElectronica': '03',
    'TiqueteElectronico': '04',
}


class AccountJournal(models.Model):
    _inherit = "account.journal"

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
        if move_type not in ["in_invoice", "in_refund"]:
            raise UserError(
                "Esta accion solo es permitida para diarios de compra-reembolso.")
        if not self.default_account_id:
            raise UserError(
                "No esta definida una cuenta predeterminada para el diario %s." % self.name)

        # As we are coming from the journal, we assume that each attachments
        # will create an invoice with a tentative to enhance with EDI / OCR..
        all_invoices = self.env['account.move']
        for attachment in attachments:
            if attachment.mimetype not in ['text/xml', 'text/plain']:
                raise UserError(_("The uploaded file is not supported. Bust be XML file."))

            try:
                root = ET.fromstring(attachment.raw)
                tipo_xml = root.tag.split('}')[-1]
                # if not root.tag.split('}')[0].find('/v4.3/') >= 0:
                # if not root.tag.split('}')[0].find(f'/v{ce_version}/') >= 0:
                # if not root.tag.split('}')[0].find(f'/v{HACIENDA_VERSION}/') >= 0:
                #     raise ValidationError(f"Version no soportada")
                if root.tag.split('}')[0].find(f'/v{HACIENDA_VERSION}/') >= 0:
                    ce_version = HACIENDA_VERSION
                elif root.tag.split('}')[0].find(f'/v4.3/') >= 0:
                    ce_version = '4.3'
                else:
                    raise ValidationError(f"Version no soportada")
            except Exception as e:
                raise ValidationError(e)
            if tipo_xml is None:
                raise ValidationError(_("Could not find document type."))

            if ce_version == '4.4':
                docu, partner_id, tipo, tipo_xml = self.l10n_cr_prepare_document(tipo_xml, attachment, move_type)
                invoice = self.l10n_cr_create_invoice(docu, partner_id, tipo, tipo_xml)
            elif ce_version == '4.3':
                docu, partner_id, tipo, tipo_xml = extractor_43.l10n_cr_prepare_document(self, tipo_xml, attachment, move_type)
                invoice = extractor_43.l10n_cr_create_invoice(self, docu, partner_id, tipo, tipo_xml)
            else:
                continue

            all_invoices |= invoice
            invoice.with_context(
                account_predictive_bills_disable_prediction=True,
                no_new_invoice=True,
            ).message_post(attachment_ids=attachment.ids)
            attachment.sudo().write({'res_model': 'account.move', 'res_id': invoice.id})

        return all_invoices

    @api.model
    def l10n_cr_prepare_document(self, tipo_xml, attachment, move_type):
        # SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
        # PARENT_ROOT = os.path.abspath(os.path.join(SITE_ROOT, os.pardir))
        # w_dirname_cert = '/data/xsd/'
        # w_path_dir_cert = PARENT_ROOT + w_dirname_cert

        file = tempfile.NamedTemporaryFile(delete=False)
        file.write(attachment.raw)
        file.close()
        filename = file.name
        if tipo_xml == 'FacturaElectronica':
            docu = FE.parseString(attachment.raw, silence=True)
            tipo = L10N_CR_VOUCHER_TYPE_MAP[tipo_xml]
            # path_fe = w_path_dir_cert + "FacturaElectronica_V4.3.xsd"
            # result = self.parse_xsd(filename, path_fe)
            # if not result['valid']:
            #     raise ValidationError(result['message'])
        elif tipo_xml == 'NotaCreditoElectronica':
            docu = NC.parseString(attachment.raw, silence=True)
            tipo = L10N_CR_VOUCHER_TYPE_MAP[tipo_xml]
            # path_nc = w_path_dir_cert + "NotaCreditoElectronica_V4.3.xsd"
            # result = self.parse_xsd(filename, path_nc)
            # if not result['valid']:
            #     raise ValidationError(result['message'])
        elif tipo_xml == 'NotaDebitoElectronica':
            docu = ND.parseString(attachment.raw, silence=True)
            tipo = L10N_CR_VOUCHER_TYPE_MAP[tipo_xml]
            # path_nc = w_path_dir_cert + "NotaDebitoElectronica_V4.3.xsd"
            # result = self.parse_xsd(filename, path_nc)
            # if not result['valid']:
            #     raise ValidationError(result['message'])
        else:
            _logger.info("Tipo de comprobante desconocido: " + tipo_xml)
            # continue
            return False, False, False, False

        subprocess.call(['rm', '-f', filename])
        if move_type == "in_invoice":
            company_id = self.company_id
            receiver = docu.get_Receptor()
            if receiver:
                if receiver.get_Identificacion().get_Numero() != company_id.vat:
                    raise ValidationError(
                        "El archivo esta dirigido a la identificacion: {} que no coincide con la identificacion de la compañia {}".format(
                            receiver.get_Identificacion().get_Numero(), self.env.company.vat))

            sender = docu.get_Emisor()
            identification_type = sender.get_Identificacion().get_Tipo()
            ident_number = sender.get_Identificacion().get_Numero()
            tin_type = self.env['ce.identification.type'].search([('code', '=', identification_type)])
            if not tin_type:
                raise ValidationError(_("Identification Type: " + identification_type + " not recognized"))
            domain = [('vat', '=', ident_number), ('identification_id', '=', tin_type.id)]
            partner_id = self.env['res.partner'].search(domain, limit=1)
            if not partner_id:
                partner_id = self.l10n_cr_create_partner_from_doc(sender)
        if move_type == "in_refund":
            sender = docu.get_Emisor()
            identification_type = sender.get_Identificacion().get_Tipo()
            ident_number = sender.get_Identificacion().get_Numero()
            tin_type = self.env['ce.identification.type'].search([('code', '=', identification_type)])
            if not tin_type:
                raise ValidationError(_("Identification Type: " + identification_type + " not recognized"))
            domain = [('vat', '=', ident_number), ('identification_id', '=', tin_type.id)]
            partner_id = self.env['res.partner'].search(domain, limit=1)
            if not partner_id:
                partner_id = self.l10n_cr_create_partner_from_doc(sender)

        return docu, partner_id, tipo, tipo_xml

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
            domain = [('name', '=', barrio_txt), ('district_id', '=', distrito_id.id)]
            barrio_id = self.env['res.country.neighborhood'].search(domain)
        partner_vals = {
            'name': partner.Nombre.encode('utf-8'),
            'commercial_name': partner.get_NombreComercial().encode(
                'utf-8') if partner.get_NombreComercial() else False,
            'identification_id': tin_type.id,
            'vat': cedula,
            'phone': str(partner.get_Telefono().get_NumTelefono()) if partner.get_Telefono() else '',
            'email': partner.get_CorreoElectronico(),
            'street': otras_senas if otras_senas else '',
            'country_id': country_id.id,
            'state_id': state_id.id if state_id else None,
            'canton_id': canton_id.id if canton_id else None,
            'distrito_id': distrito_id.id if distrito_id else None,
            'neighborhood_id': barrio_id.id if barrio_id else None,
            'is_company': True if cedula_type == '02' else False
        }

        new_partner = self.env['res.partner'].create(partner_vals)
        return new_partner

    @api.model
    def l10n_cr_create_get_product(self, lineadetalle, partner_id, company_id, currency_id):
        ProductProduct = self.env['product.product']
        ProductCabys = self.env['ce.product.cabys']
        cabys_code = lineadetalle.get_CodigoCABYS()
        product_name = lineadetalle.get_Detalle().strip()
        product_code = ""
        barcode = ""
        default_code = ""
        args = [('partner_id', '=', partner_id.id),
                '|',
                ('product_name', '=', product_name)]
        for codigo_comercial in lineadetalle.get_CodigoComercial():
            code_type = codigo_comercial.get_Tipo()
            code_value = codigo_comercial.get_Codigo().strip()
            if code_type == '01':
                product_code = code_value
                args.append(('product_code', '=', product_code))
            elif code_type == '02':  # codigo del comprador
                default_code = code_value
            elif code_type == '03':  # Barcode
                barcode = code_value
            elif code_type == '04' and not default_code:  # codigo de uso interno
                default_code = code_value
            elif code_type == '99' and not default_code:
                default_code = code_value
        if not product_code:
            del (args[1])

        products = []
        # first try to get the product by searching using supplier_id
        # product_name or product_code
        if not products and partner_id:
            suppliers = self.env['product.supplierinfo'].search(args)
            if suppliers:
                products = ProductProduct.search([('seller_ids', 'in', suppliers.ids)], limit=1)
        # Product not found by supplier
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
            product_cabys_id = ProductCabys.search([('code', '=', cabys_code)], limit=1)
            vals = {
                'name': product_name,
                'type': 'consu',
                'product_cabys_id': product_cabys_id.id,
                'company_id': company_id.id,
                'sale_ok': False,
            }
            if journal_type == "sale":
                vals['list_price'] = price_unit
            if journal_type == "purchase":
                vals['standard_price'] = price_unit
            # if codigo_cabys and len(codigo_cabys) == 13:
            #     cabys = self.env['ce.product.cabys'].search([('code', '=', codigo_cabys)])
            #     vals['product_cabys_id'] = cabys.id
            uom_code_id = self.env['uom.uom'].search([('code', '=', lineadetalle.get_UnidadMedida())])
            if not uom_code_id:
                uom_code_id = self.env['uom.uom'].search([('code', '=', 'Unid')])  # should always exist in DB
            # if uom_code_id.l10n_cr_uom_type == 'service':
            #     vals['type'] = 'service'
            vals['uom_id'] = uom_code_id.id
            vals['uom_po_id'] = uom_code_id.id
            if barcode:
                vals['barcode'] = barcode
                vals['default_code'] = barcode
            taxes = lineadetalle.get_Impuesto()
            supplier_taxes_id = []
            for impl in taxes:
                imp = self.env['account.tax'].search([('code_cr', '=', impl.get_Codigo()),
                                                      ('active', '=', True),
                                                      ('type_tax_use', '=', 'purchase'),
                                                      ('amount', '=', impl.get_Tarifa()),
                                                      ('company_id', '=', company_id.id)
                                                      ])

                if imp:
                    supplier_taxes_id.append(imp[0].id)
                # TODO what if the tax doesn't exist in the system
                # TODO check if price_lists are being used in the system
                # TODO also check if purchases are being used in the system and add the product to the supplier

            if len(supplier_taxes_id) > 0:
                vals['supplier_taxes_id'] = [Command.set(supplier_taxes_id)]
            supplierinfo = {
                'partner_id': partner_id.id,
                'product_name': product_name,
                'price': price_unit,
                'currency_id': currency_id.id,
                'min_qty': 1,
            }
            if product_code:
                supplierinfo['product_code'] = product_code
            vals['seller_ids'] = [Command.create(supplierinfo)]
            products = ProductProduct.create(vals)

        return products

    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    def l10n_cr_create_invoice(self, docu, partner_id, tipo, voucher_type_txt):
        invoice_vals = self._l10n_cr_prepare_invoice_model(docu, partner_id, tipo, voucher_type_txt)
        invoice_vals['journal_id'] = self.id
        invoice_id = self.env['account.move'].create(invoice_vals)
        default_activity_from_xml = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cr_invoice_receptor.create_activity_from_xml')

        if default_activity_from_xml:
            account_move_model_id = self.env['ir.model']._get_id('account.move')
            activity_record = {
                'activity_type_id': 1,
                'res_id': invoice_id.id,
                'res_model_id': account_move_model_id,
                'date_deadline': datetime.now() + timedelta(hours=24),
                'user_id': self._uid or SUPERUSER_ID,
                'note': 'Nueva fatura de proveedor',
                'summary': 'Nueva fatura de proveedor importada',
            }
            self.env['mail.activity'].create(activity_record)

        return invoice_id

    def _l10n_cr_prepare_invoice_model(self, docu, partner_id, tipo, voucher_type_txt):
        move_type = self._context.get("default_move_type", "in_invoice")
        company_id = self.company_id
        invoice_type = move_type
        # if tipo == '03':
        #     invoice_type = 'in_refund'

        plazo_credito = docu.get_PlazoCredito()
        medios_pago = docu.get_ResumenFactura().get_MedioPago()
        medio_pago = ''

        if medios_pago:
            list_medio_pago = [mp.get_TipoMedioPago() for mp in medios_pago]
            if '01' in list_medio_pago:
                medio_pago = 'Contado'
            elif '02' in list_medio_pago:
                medio_pago = 'Crédito'
            elif '03' in list_medio_pago:
                medio_pago = 'Consignación'
            elif '04' in list_medio_pago:
                medio_pago = 'Apartado'
            elif '05' in list_medio_pago:
                medio_pago = 'Arrendamiento con opción de compra'
            elif '06' in list_medio_pago:
                medio_pago = 'Arrendamiento en función financiera'
            elif '99' in list_medio_pago:
                medio_pago = 'Otros'

        fpos = None  # TODO complete fiscal position
        voucher_type_code = L10N_CR_VOUCHER_TYPE_MAP[voucher_type_txt]
        if not voucher_type_code:
            raise ValidationError(_("Voucher Type not found: " + voucher_type_code))
        issue_date = docu.get_FechaEmision()
        condition_sale = docu.get_CondicionVenta()

        # journal_pay_ids = []
        # for mp in medios_pago:
        #     journal_pay = self.env['account.journal'].search([('code_cr', '=', mp.get_TipoMedioPago())], limit=1)
        #     if len(journal_pay) == 1:
        #         journal_pay_ids.append(journal_pay.id)

        # l10n_cr_payment_method_ids = []
        # for mp in medios_pago:
        #     journal_pay = self.env['l10n_cr.payment_method'].search([('code', '=', mp.get_TipoMedioPago())], limit=1)
        #     if len(journal_pay) == 1:
        #         l10n_cr_payment_method_ids.append(journal_pay.id)

        EconomicActivity = self.env['ce.economic.activity']
        economic_activity_id = EconomicActivity.search([('code', '=', docu.get_CodigoActividadEmisor())], limit=1)
        if not economic_activity_id:
            response, vals = get_economic_activities(partner_id.vat)
            if response.status_code in (200, 202) and len(response._content) > 0:
                content = json.loads(str(response._content, 'utf-8'))
                if content.get('actividades'):
                    actividades = content['actividades']
                    if len(actividades) < 1:
                        raise ValidationError(
                            "No se encontraron actividades económicas para la identificación: " + str(partner_id.vat))

                    for a in actividades:
                        if a['codigo'] == docu.get_CodigoActividadEmisor():
                            activity = EconomicActivity.create({
                                'code': a['codigo'],
                                'name': a['descripcion'],
                            })
                            economic_activity_id = activity
            else:
                raise ValidationError(_("Economic Activity not found: " + docu.get_CodigoActividadEmisor()))

        if tipo == '01':
            voucher_type_id = self.env.ref('l10n_cr_invoice.voucher_01')
        elif tipo == '03':
            voucher_type_id = self.env.ref('l10n_cr_invoice.voucher_03')
            invoice_type = 'in_refund'
        else:
            voucher_type_id = self.env.ref('l10n_cr_invoice.voucher_02')

        invoice_vals = {
            'move_type': invoice_type,
            'ref': docu.get_NumeroConsecutivo() if invoice_type in ('in_invoice', 'in_refund') else False,
            # 'l10n_cr_document_number': docu.get_Clave(),
            'l10n_cr_document_name': docu.get_Clave(),
            'l10n_cr_document_number': docu.get_NumeroConsecutivo(),
            'partner_id': partner_id.id,
            'invoice_date': fields.Date.to_string(issue_date),
            'company_id': company_id.id,
            'narration': 'Plazo de credito %s dias. Medio de pago: %s ' % (plazo_credito, medio_pago),
            'xml_amount_tax': float(docu.get_ResumenFactura().get_TotalImpuesto()),
            'xml_amount_total': float(docu.get_ResumenFactura().get_TotalComprobante()),
            'l10n_cr_supplier_economic_activity_id': economic_activity_id.id,
            'voucher_type_id': voucher_type_id.id,
        }

        if condition_sale == "02":
            try:
                credit_term = int(plazo_credito or 0)
            except ValueError as e:
                credit_term = 0
            # invoice_date_due = issue_date + relativedelta(days=int(plazo_credito or 0))
            invoice_date_due = issue_date + relativedelta(days=credit_term)
            invoice_vals.update({"invoice_date_due": invoice_date_due})
        else:
            payment_term_id = self.env['account.payment.term'].search([('payment_type_id.code', '=', condition_sale)],
                                                                      limit=1)
            invoice_vals.update({"invoice_payment_term_id": payment_term_id.id})

        # if l10n_cr_payment_method_ids:
        #     invoice_vals['l10n_cr_payment_method_ids'] = [(6, 0, l10n_cr_payment_method_ids)]
        if (docu.get_ResumenFactura().get_CodigoTipoMoneda()
                and docu.get_ResumenFactura().get_CodigoTipoMoneda().get_CodigoMoneda() != 'CRC'):
            self._l10n_cr_gen_other_currency(docu, invoice_vals)
        fiscal_position = False
        invoice_line = self._l10n_cr_gen_model_invoice_line(docu, partner_id)

        # FiscalPosition
        if fiscal_position:
            invoice_vals['fiscal_position_id'] = fiscal_position[0].id
        invoice_vals['invoice_line_ids'] = [(0, 0, line.PrepareInvoiceLine()) for line in invoice_line]
        other_charges = docu.get_OtrosCargos()
        if other_charges:
            discount_charges = self._l10n_cr_gen_discount_charges(docu)
            invoice_vals['invoice_line_ids'].extend(
                [(0, 0, line.PrepareDescuentosORecargosLine()) for line in discount_charges])

        return invoice_vals

    def _l10n_cr_gen_model_invoice_line(self, docu, partner_id):
        """Crea las lineas de factura.

            :param object docu: Instancia del Elemento raiz.
            """
        move_type = self._context.get("default_move_type", "in_invoice")
        company_id = self.company_id
        invoice_type = move_type
        invoice = Invoice()
        service_details = docu.get_DetalleServicio()
        for l in service_details.get_LineaDetalle():
            product_name = l.get_Detalle()
            default_product_from_xml = self.env['ir.config_parameter'].sudo().get_param(
                'l10n_cr_invoice_receptor.l10n_cr_create_product_from_xml')

            line_taxes = []
            if l.get_Impuesto():
                for i in l.get_Impuesto():
                    if i.get_Exoneracion():
                        exoneration = i.get_Exoneracion()
                        exo = self.env["ce.exoneration"].search(
                            [('document_number', '=', exoneration.get_NumeroDocumento())], limit=1)
                        if not exo:
                            raise ValidationError(
                                _(f"Exoneration not found in system: {exoneration.get_NumeroDocumento()}"))

                        fpos = self.env["account.fiscal.position"].search([('exoneration_authorization', '=', True),
                                                                           ('exoneration_id', '=', exo.id)])
                        if not fpos:
                            raise ValidationError(
                                _(f"Fiscal Position with exoneration not found in system: {exoneration.get_NumeroDocumento()}"))

                        fiscal_position = fpos

                    codigo_cr = i.get_Codigo()
                    tarifa_cr = i.get_CodigoTarifaIVA()
                    if i.get_Exoneracion():
                        for tax_map in fpos.tax_ids:
                            if tax_map.tax_dest_id:
                                codigo_cr = tax_map.tax_dest_id.code_cr
                                tarifa_cr = tax_map.tax_dest_id.iva_tax_rate

                    search_params = [('code_cr', '=', codigo_cr),
                                     ('type_tax_use', '=', 'sale' if move_type == 'out_invoice' else 'purchase'),
                                     ('company_id', '=', company_id.id),
                                     ('country_id', '=', self.env.ref("base.cr").id)
                                     ]
                    if tarifa_cr:
                        search_params.append(('iva_tax_rate', '=', tarifa_cr))

                    tax_id = self.env['account.tax'].search(search_params)

                    # TODO CodigoTarifa 4.3 para el impuesto revisar esto
                    # Tarifa reducida el receptor debe contar con la debida autorizacion

                    if not tax_id:
                        journal_type = 'sale' if invoice_type == 'out_invoice' else 'purchase'
                        _logger.info(
                            "Tax not found in system: " + i.get_Codigo() + " with tarifa: " + str(
                                i.get_Tarifa()))

                        if i.get_Codigo() in ('99', '05'):
                            _logger.info(
                                'Impuesto con codigo (' + i.get_Codigo()
                                + ') no se encuentra en el sistema, favor crearlo antes de importar. '
                                  'Este impuesto es configurado como monto fijo y puede indicar 0.0 en dicho monto, '
                                  'el valor sera el que venga en la factura de venta.')
                        _logger.info(
                            'Impuesto de ' + journal_type + ' con codigo (' + i.get_Codigo() + ') con tarifa="' + str(
                                i.get_Tarifa()) + '" no se encuentra en el sistema, favor crearlo antes de importar')

                        raise ValidationError(_(f"Tax not found in system {journal_type}: {i.get_Codigo()} "
                                                f"with amount: {str(i.get_Tarifa())} in company active."))

                    line_taxes.append(tax_id[0].id)
            # else:
            #     # Se establece exento si no llega un impuesto.
            #     search_params = [('code_cr', '=', '01'),
            #                      ('iva_tax_rate', '=', '01'),
            #                      ('active', '=', True),
            #                      ('type_tax_use', '=', 'sale' if move_type == 'out_invoice' else 'purchase'),
            #                      ('company_id', '=', company_id.id)
            #                      ]
            #     tax_id = self.env['account.tax'].search(search_params)
            #     line_taxes.append(tax_id[0].id)

            invoice_line = InvoiceLine(
                name=product_name,
                total=l.get_MontoTotalLinea(),
                quantity=float(l.get_Cantidad()),
                price=float(l.get_PrecioUnitario()),
                tax_ids=line_taxes,
            )
            if default_product_from_xml:
                product_id = self.l10n_cr_create_get_product(l, partner_id, company_id, company_id.currency_id)
                product_account = self.get_invoice_line_account(invoice_type, product_id, None, company_id)
                invoice_line.product_id = product_id.id
                invoice_line.product_uom_id = product_id.uom_id.id
                invoice_line.account_id = product_account.id if product_account else None
            total_amount_discount = 0
            for discount in l.get_Descuento():
                total_amount_discount += float(discount.get_MontoDescuento())
            if total_amount_discount > 0:
                price_subtotal = float(l.get_MontoTotal())
                discount_percent = round((total_amount_discount / price_subtotal) * 100, 2)
                if discount_percent > 0:
                    invoice_line.discount = discount_percent
                    invoice_line.discount_type_code = discount.get_CodigoDescuento()

            _logger.info(invoice_line)
            invoice.addLine(invoice_line)

        return invoice.getLines()

    def _l10n_cr_gen_discount_charges(self, docu):
        """Crea las lineas de descuentos o recargos.

            :param object docu: Instancia del Elemento raiz.
            """

        invoice = Invoice()
        other_charges = docu.get_OtrosCargos()
        # for line in descuentos_recargos.get_DescuentoItem():
        for line in other_charges:
            invoice_line = InvoiceLine(
                name=line.get_Detalle(),
                quantity=1,
                price=float(line.get_MontoCargo()),
            )
            invoice.addLine(invoice_line)

        return invoice.getLines()

    @api.model
    def _l10n_cr_gen_other_currency(self, docu, invoice_vals):
        currency_code = docu.get_ResumenFactura().get_CodigoTipoMoneda().get_CodigoMoneda()
        currency_rate = docu.get_ResumenFactura().get_CodigoTipoMoneda().get_TipoCambio()
        ResCurrency = self.env['res.currency'].sudo()
        currency_id = ResCurrency.with_context(active_test=False).search([('name', '=', currency_code)], limit=1)
        if not currency_id:
            _logger.info("Tipo de moneda no encontrada.")

        if not currency_id.active:
            currency_id.active = True

        invoice_vals["currency_id"] = currency_id.id
        if currency_id and currency_id.active:
            invoice_vals["currency_rate"] = currency_rate

        return currency_id

    @api.model
    def parse_xsd(self, xml_file, xsd_file):
        result = {}
        try:
            xml_doc = etree.parse(xml_file)
            xmlschema = etree.XMLSchema(etree.parse(xsd_file))
            is_valid = xmlschema.validate(xml_doc)

            validation_errors = []
            if not is_valid:
                for error in xmlschema.error_log:
                    if "Missing child element(s)" not in error.message:
                        validation_errors.append(f"Error: {error.message} (línea {error.line})")

            if validation_errors:
                raise etree.DocumentInvalid(", ".join(validation_errors))

            result["message"] = "El documento XML ha sido validado correctamente con respecto al esquema XSD."
            result["valid"] = True

        except etree.XMLSyntaxError as e:
            result["message"] = f"Error de sintaxis XML: {str(e)}"
            result["valid"] = False

        except etree.DocumentInvalid as e:
            result["message"] = f"Error de validación: {str(e)}"
            result["valid"] = False

        except Exception as e:
            result["message"] = f"Error inesperado: {str(e)}"
            result["valid"] = False

        return result
