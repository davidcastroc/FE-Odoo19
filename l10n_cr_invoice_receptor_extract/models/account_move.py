# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.addons.mail.models.ir_attachment import IrAttachment
from odoo.exceptions import UserError, ValidationError
from odoo.addons.l10n_cr_invoice.models import FE
from odoo.addons.l10n_cr_invoice.models import NC
from odoo.addons.l10n_cr_invoice.models import ND
from odoo.addons.l10n_cr_invoice_receptor.models.account_journal import L10N_CR_VOUCHER_TYPE_MAP
from ..FE43 import extractor_43
from odoo.addons.l10n_cr_invoice.hacienda_api import HACIENDA_VERSION
from . import api_import_mail
from odoo import SUPERUSER_ID
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from lxml import etree
import base64
import tempfile
import pathlib
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_order_id = fields.Many2one("purchase.order")
    nx_warning_message = fields.Char(readonly=True)
    has_processing = fields.Boolean(default=False)

    # Reimplementando
    def _compute_show_banners(self):
        super()._compute_show_banners()
        for record in self:
            record.extract_can_show_banners = False

    def _compute_show_send_button(self):
        super()._compute_show_send_button()
        for record in self:
            record.extract_can_show_send_button = False

    extract_can_show_banners = fields.Boolean("Can show the ocr banners", compute=_compute_show_banners)
    extract_can_show_send_button = fields.Boolean('Can show the ocr send button', compute='_compute_show_send_button')

    @api.model
    def _contact_iap_extract(self, pathinfo, params):
        # Suprimiendo la llamada al api: https://extract.api.odoo.com
        # return {}
        return {'status': 'error_status'}

    def action_manual_extract_xml(self):
        """Digitaliza el XML adjunto al correo."""

        self.ensure_one()
        self.nx_warning_message = ''

        if self.state != 'draft':
            return False

        attachments = self.attachment_ids.filtered(lambda l: l.mimetype in ['application/xml', 'text/xml', 'text/plain'])
        if not attachments:
            attachments = []
            attachments_zip = self.attachment_ids.filtered(lambda l: l.mimetype in ['application/zip'])
            for att in attachments_zip:
                attachment_xml = api_import_mail.l10n_cr_get_attachment_zip(att.raw)
                if attachment_xml:
                    attachments.append(attachment_xml)

        if not attachments:
            self.nx_warning_message = _("No attachment XML was provided")
            return

        # SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
        # PARENT_ROOT = os.path.abspath(os.path.join(SITE_ROOT, os.pardir))
        # PARENT_ROOT = PARENT_ROOT.replace('l10n_cr_invoice_receptor_extract', 'l10n_cr_invoice_receptor')
        # w_dirname_xsd = '/data/xsd/'
        # w_path_dir_cert = PARENT_ROOT + w_dirname_xsd

        for attachment in attachments:
            try:
                if isinstance(attachment, bytes):
                    root = ET.fromstring(attachment)
                    xml_bytes = attachment
                else:
                    root = ET.fromstring(attachment.raw)
                    xml_bytes = attachment.raw

                tipo_xml = root.tag.split('}')[-1]
                if root.tag.split('}')[0].find(f'/v{HACIENDA_VERSION}/') >= 0:
                    ce_version = HACIENDA_VERSION
                elif root.tag.split('}')[0].find(f'/v4.3/') >= 0:
                    ce_version = '4.3'
                else:
                    self.nx_warning_message = f"Version {root.tag.split('}')[0].find('/v4.3/')} no soportada"

                # if not root.tag.split('}')[0].find('/v4.3/') >= 0:
                #     # doc_version = 4.3
                #     self.nx_warning_message = f"Version {root.tag.split('}')[0].find('/v4.3/')} no soportada"
            except Exception as e:
                self.nx_warning_message = e
                return

            if tipo_xml is None:
                self.nx_warning_message = _("Could not find document type.")
                return

            if ce_version == '4.4':
                docu, partner_id, tipo, tipo_xml = self.l10n_cr_prepare_document(tipo_xml, attachment, xml_bytes)
                if docu:
                    self._l10_cr_update_invoice_model(docu, partner_id, tipo, tipo_xml)
            elif ce_version == '4.3':
                docu, partner_id, tipo, tipo_xml = extractor_43.l10n_cr_prepare_document(self, tipo_xml, attachment, self.move_type)
                if docu:
                    self._l10_cr_update_invoice_model43(docu, partner_id, tipo, tipo_xml)
                # invoice = extractor_43.l10n_cr_create_invoice(self, docu, partner_id, tipo, tipo_xml)
            else:
                continue

    @api.model
    def l10n_cr_prepare_document(self, tipo_xml, attachment, xml_bytes):
        # SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
        # PARENT_ROOT = os.path.abspath(os.path.join(SITE_ROOT, os.pardir))
        # PARENT_ROOT = PARENT_ROOT.replace('l10n_cr_invoice_receptor_extract', 'l10n_cr_invoice_receptor')
        # w_dirname_xsd = '/data/xsd/'
        # w_path_dir_cert = PARENT_ROOT + w_dirname_xsd
        file = tempfile.NamedTemporaryFile(delete=False)
        file.write(xml_bytes)
        file.close()
        # filename = file.name
        if tipo_xml == 'FacturaElectronica':
            docu = FE.parseString(xml_bytes, silence=True)
            tipo = L10N_CR_VOUCHER_TYPE_MAP[tipo_xml]
            # path_fe = w_path_dir_cert + "FacturaElectronica_V4.4.xsd"
            # result = self.env["account.journal"].parse_xsd(filename, path_fe)
            # if not result['valid']:
            #     self.nx_warning_message = result['message']
            #     return

        elif tipo_xml == 'NotaCreditoElectronica':
            docu = NC.parseString(xml_bytes, silence=True)
            tipo = L10N_CR_VOUCHER_TYPE_MAP[tipo_xml]
            # path_nc = w_path_dir_cert + "NotaCreditoElectronica_V4.4.xsd"
            # result = self.env["account.journal"].parse_xsd(filename, path_nc)
            # if not result['valid']:
            #     self.nx_warning_message = result['message']
            #     return

        elif tipo_xml == 'NotaDebitoElectronica':
            docu = ND.parseString(xml_bytes, silence=True)
            tipo = L10N_CR_VOUCHER_TYPE_MAP[tipo_xml]
            # path_nc = w_path_dir_cert + "NotaDebitoElectronica_V4.4.xsd"
            # result = self.env["account.journal"].parse_xsd(filename, path_nc)
            # if not result['valid']:
            #     self.nx_warning_message = result['message']
            #     return
        elif tipo_xml == 'MensajeHacienda':
            # Omitiendo MensajeHacienda
            return False, False, False, False
            # continue
        else:
            _logger.info("Tipo de comprobante desconocido: " + tipo_xml)
            return False, False, False, False
            # continue

        company_id = self.company_id
        move_type = self.move_type
        if move_type == "in_invoice":
            receiver = docu.get_Receptor()
            if receiver and receiver.get_Identificacion().get_Numero() != company_id.vat:
                self.nx_warning_message = "El archivo esta dirigido a la identificacion: {} que no coincide con la identificacion de la compañia {}".format(
                    receiver.get_Identificacion().get_Numero(), company_id.vat)
                return False, False, False, False

            sender = docu.get_Emisor()
            identification_type = sender.get_Identificacion().get_Tipo()
            ident_number = sender.get_Identificacion().get_Numero()
            tin_type = self.env['ce.identification.type'].search([('code', '=', identification_type)])

            if not tin_type:
                self.nx_warning_message = _("Identification Type: " + identification_type + " not recognized")
                return False, False, False, False

            domain = [('vat', '=', ident_number), ('identification_id', '=', tin_type.id)]
            partner_id = self.env['res.partner'].search(domain, limit=1)

            if not partner_id:
                partner_id = self.env["account.journal"].l10n_cr_create_partner_from_doc(sender)
        else:
            return False, False, False, False

        # try:
        #     self._l10_cr_update_invoice_model(docu, partner_id, tipo, tipo_xml)
        # except Exception as e:
        #     self.nx_warning_message = e

        return docu, partner_id, tipo, tipo_xml

    def _l10_cr_update_invoice_model(self, docu, partner_id, tipo, voucher_type_txt):
        invoice_vals = self.journal_id._l10n_cr_prepare_invoice_model(docu, partner_id, tipo, voucher_type_txt)
        invoice_vals['extract_status'] = "success"
        self.write(invoice_vals)
        default_activity_from_xml = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cr_invoice_receptor.create_activity_from_xml')

        if default_activity_from_xml:
            account_move_model_id = self.env['ir.model']._get_id(self._name)
            activity_record = {
                'activity_type_id': 1,
                'res_id': self.id,
                'res_model_id': account_move_model_id,
                'date_deadline': datetime.now() + timedelta(hours=24),
                'user_id': self._uid or SUPERUSER_ID,
                'note': 'Nueva fatura de proveedor',
                'summary': 'Nueva fatura de proveedor importada',
            }
            self.env['mail.activity'].create(activity_record)

        return

    def _l10_cr_update_invoice_model43(self, docu, partner_id, tipo, voucher_type_txt):
        invoice_vals = extractor_43._l10n_cr_prepare_invoice_model(self, docu, partner_id, tipo, voucher_type_txt)
        invoice_vals['extract_status'] = "success"
        self.write(invoice_vals)
        default_activity_from_xml = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_cr_invoice_receptor.create_activity_from_xml')

        if default_activity_from_xml:
            account_move_model_id = self.env['ir.model']._get_id(self._name)
            activity_record = {
                'activity_type_id': 1,
                'res_id': self.id,
                'res_model_id': account_move_model_id,
                'date_deadline': datetime.now() + timedelta(hours=24),
                'user_id': self._uid or SUPERUSER_ID,
                'note': 'Nueva fatura de proveedor',
                'summary': 'Nueva fatura de proveedor importada',
            }
            self.env['mail.activity'].create(activity_record)

        return

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # EXTENDS mail mail.thread

        def _get_invoice_xml_consecutive(invoice_att_xml):
            namespaces = invoice_att_xml.nsmap
            inv_xmlns = namespaces.pop(None)
            namespaces['inv'] = inv_xmlns
            document_number = invoice_att_xml.xpath("inv:Clave", namespaces=namespaces)[0].text
            return document_number

        def _get_bill_exist(document_number):
            domain = [('l10n_cr_document_number', '=', document_number)]
            return self.search(domain, limit=1)

        default_journal_id = custom_values['journal_id']
        journal = self.env['account.journal'].browse(default_journal_id)
        electronic_number = None
        new_attachments = []
        other_attachments = []
        if journal.alias_auto_extract_xml_only:
            attachments = msg_dict.get('attachments', [])

            any_xml = []
            for attachment in attachments:
                # _logger.info(attachment)
                if isinstance(attachment, IrAttachment):
                    _logger.info(attachment.name)
                    if attachment.mimetype in ['text/xml', 'text/plain']:
                        any_xml.append(attachment.raw)
                else:
                    fname = attachment[0]
                    _logger.info(fname)
                    if pathlib.Path(fname.upper()).suffix == '.XML':
                        any_xml.append(attachment[1])
                        new_attachments.append(attachment)
                    elif pathlib.Path(fname.upper()).suffix == '.ZIP':
                        attachment_xml = api_import_mail.l10n_cr_get_attachment_zip(attachment[1])
                        any_xml.append(attachment_xml)
                        new_attachments.append(attachment)
                    else:
                        other_attachments.append(attachment)

            list_attachments = []
            for attachment in any_xml:
                try:
                    root = ET.fromstring(attachment)
                    document_type = root.tag.split('}')[-1]
                except Exception as e:
                    _logger.error(e)
                    continue

                if document_type is None:
                    _logger.info(_("Could not find document type."))
                    continue

                if document_type not in api_import_mail.AVAILABLE_VOUCHER_TYPES:
                    _logger.info("The electronic receipt is unknown, it will simply be ignored")
                    continue

                attachencode = base64.encodebytes(attachment) if isinstance(attachment, bytes) else (
                    base64.encodebytes(attachment.encode('utf-8')))

                invoice_xml = etree.fromstring(base64.b64decode(attachencode))
                electronic_number = _get_invoice_xml_consecutive(invoice_xml)

                exist_invoice = _get_bill_exist(electronic_number)
                if document_type == 'MensajeHacienda':
                    if exist_invoice:
                        self.l10n_cr_create_ir_attachment_invoice(exist_invoice, attachment, 'application/xml')
                        # attachment_id = self.l10n_cr_create_ir_attachment_invoice(exist_invoice, attachment, 'application/xml')
                        # exist_invoice.message_post(attachment_ids=[attachment_id.id])

                        _logger.info(_('Document already previously registered.'))
                        return exist_invoice

                    continue
                if document_type == 'FacturaElectronica' and exist_invoice:
                    _logger.info("Its duplicate Invoice (%s), Deleting Mail" % exist_invoice.ref)
                    continue
                if document_type == 'NotaCreditoElectronica' and exist_invoice:
                    _logger.info("Its duplicate Invoice (%s), Deleting Mail" % exist_invoice.ref)
                    continue

                list_attachments.append(attachment)
                msg_dict['attachments'] = new_attachments

            if not list_attachments:
                raise ValidationError(_("No valid xml document was found"))

        res = super().message_new(msg_dict, custom_values)
        if journal.alias_auto_extract_xml_only and electronic_number:
            res.write({'l10n_cr_document_number': electronic_number, 'has_processing': True})

        pdf_attachment = []
        for attach in other_attachments:
            attachencode = base64.encodebytes(attach[1]) if isinstance(attach[1], bytes) else base64.encodebytes(attach[1].encode('utf-8'))
            attachment_id = self._create_new_attachment(res, attach[0], attachencode, 'application/pdf')
            pdf_attachment.append(attachment_id.id)

        # res.message_post(body='PDF', attachment_ids=pdf_attachment)
        # last_message = res.message_ids[0]
        # last_message.attachment_ids = [(4, attachment_id.id)]

        return res

    def _create_new_attachment(self, invoice, fname, content, mimetype):
        ir_attachment = self.env['ir.attachment'].create({
            'name': fname,
            'type': 'binary',
            'datas': content,
            'store_fname': fname,
            'res_model': self._name,
            'res_id': invoice.id,
            'mimetype': mimetype
        })

        return ir_attachment

    def _message_post_after_hook(self, new_message, message_values):
        # EXTENDS mail mail.thread
        # When posting a message, check the attachment to see if it's an invoice and update with the imported data.
        res = super()._message_post_after_hook(new_message, message_values)
        journal = self.journal_id
        if journal.alias_auto_extract_xml_only:
            attachments = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', self.id)])
            for attch in attachments:
                if len(self.message_ids) > 0:
                    if attch not in self.message_ids[0].attachment_ids:
                        self.message_ids[0].attachment_ids += attch

        return res

    def l10n_cr_create_ir_attachment_invoice(self, invoice, attach, mimetype):
        content = attach
        if isinstance(attach, str):
            content = attach.encode('utf-8')
        ir_attachment = self.env['ir.attachment'].create({
            'name': invoice.l10n_cr_document_number,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'store_fname': invoice.l10n_cr_document_number,
            'res_model': self._name,
            'res_id': invoice.id,
            'mimetype': mimetype
        })

        return ir_attachment

    def _check_and_decode_attachment(self, attachments):
        # Suprimiendo la logica de este metodo para q no elimine adjuntos.
        return False

    # ===== CRONs =====

    @api.model
    def cron_l10n_cr_digitize_xml(self):
        """"""
        invoices = self.search([('move_type', '=', 'in_invoice'),
                                ('state', '=', 'draft'),
                                ('extract_status', 'not in', ['success'])])
        for doc in invoices:
            doc.action_manual_extract_xml()
