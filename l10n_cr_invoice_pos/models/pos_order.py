# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from datetime import datetime
import pytz
import random
import phonenumbers
import logging

_logger = logging.getLogger(__name__)
L10N_CR_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
L10N_CR_VOUCHER_TYPE_MAP = {
    "FE": "01",
    "NC": "03",
    "TE": "04",
}


class PosOrder(models.Model):
    _inherit = "pos.order"

    reference_code_id = fields.Many2one("ce.reference.code", string="Reference Code", copy=False)
    pos_order_id = fields.Many2one("pos.order", string="Documento de referencia", required=False, copy=False)
    document_id = fields.Many2one('ce.document', string="Document", readonly=True, copy=False)
    voucher_type_id = fields.Many2one(related="document_id.voucher_type_id", string="Tipo de documento", store=True)
    voucher_number = fields.Char(string="Voucher Number")
    date_issue = fields.Datetime(related="document_id.date_issue", string="Fecha y Hora Creacion documento", store=True)
    number = fields.Char(related="document_id.number", string="Consecutive", store=True)
    clave_cr = fields.Char(related="document_id.name", string="Clave", store=True)
    ind_state = fields.Selection(related="document_id.ind_state", string="Hacienda State")
    reference_nc = fields.Char()

    # QR
    QR_code = fields.Binary(related="document_id.QR_code", string="Code QR")

    _sql_constraints = [
        ('doc_company_uniq', 'unique (document_id, company_id)',
         "El documento de Comprobante Electronico debe ser único por compañia"),
    ]

    # === BUSINESS METHODS ===#

    @api.model
    def get_from_ui(self, order):
        """Este metodo es llamado desde el POS al dar clik en Refund"""
        pos_order = self.sudo().search([('name', '=', order)])  # TODO: Hacer la busqueda por el consecutivo fiscal.
        voucher_type_code = pos_order.voucher_type_id.code
        return {
            'reference_nc': pos_order.clave_cr,
            'voucher_code': voucher_type_code,
        }

    def _prepare_invoice_vals(self):
        result = super(PosOrder, self)._prepare_invoice_vals()
        if self.session_id.company_id.country_id.code == 'CR' and self.config_id.invoice_journal_id.l10n_cr_fiscal_journal:
            terminal_id = self.session_id.config_id.terminal_id
            result['terminal_id'] = terminal_id.id
            if result['move_type'] == 'out_refund' and self.config_id.invoice_journal_id.l10n_cr_fiscal_journal:
                result["numero_ref"] = self.reference_nc

        return result

    def _get_invoice_lines_values(self, line_values, pos_order_line):
        result = super(PosOrder, self)._get_invoice_lines_values(line_values, pos_order_line)
        if self.session_id.company_id.country_id.code == 'CR' and self.config_id.invoice_journal_id.l10n_cr_fiscal_journal:
            if line_values['discount']:
                result['l10n_cr_discount_type_code'] = "07"
        return result

    @api.model
    def _process_order(self, order, existing_order):
        """" es llamado por create_from_ui """

        res = super(PosOrder, self)._process_order(order, existing_order)
        nc_bool = False
        reference_nc = ''

        for line in order.get('lines'):
            if line[2].get('refunded_orderline_id'):
                nc_bool = True
                refunded_orderline_id = line[2].get('refunded_orderline_id')
                order_line = self.env['pos.order.line'].browse(int(refunded_orderline_id))
                if order_line:
                    reference_nc = order_line.order_id.clave_cr

        # Permite agregar el codigo de referencia en caso de ser una nota de credito
        if nc_bool and reference_nc:
            order_obj = self.search([('id', '=', res)])
            reference_code = self.env['ce.reference.code'].search([('code', '=', '01')], limit=1)
            if len(order_obj) > 0:
                order_obj.write({
                    'reference_nc': reference_nc,
                    'reference_code_id': reference_code.id,
                })

        return res

    @api.model
    def sync_from_ui(self, orders):
        """
        """

        res = super(PosOrder, self).sync_from_ui(orders)
        if (
                len(orders) > 0
                and orders[0].get("session_id")
                and self.env["pos.session"].browse(orders[0]["session_id"]).config_id.l10n_cr_fiscal_journal
        ):
            for record in res['pos.order']:
                order = self.browse(record['id'])
                if self.l10n_cr_can_create_document(order):
                    nc_bool = False
                    reference_nc = ''
                    if order.reference_nc:
                        nc_bool = True
                        reference_nc = order.reference_nc

                    terminal_id = order.session_id.config_id.terminal_id
                    if not terminal_id:
                        return False

                    if nc_bool:
                        if order.account_move and order.account_move.document_id:
                            order.document_id = order.account_move.document_id.id
                        else:
                            order.l10n_cr_create_document(terminal_id,
                                                          code=L10N_CR_VOUCHER_TYPE_MAP['NC'],
                                                          reference_nc=reference_nc)
                    else:
                        if order.account_move and order.account_move.document_id:
                            order.document_id = order.account_move.document_id.id
                        else:
                            order.l10n_cr_create_document(terminal_id, code=L10N_CR_VOUCHER_TYPE_MAP['TE'])

                    if order.document_id:
                        record['number'] = order.number
                        record['clave_cr'] = order.clave_cr
                        record['voucher_number'] = order.voucher_type_id.name
                        record['QR_code'] = order.QR_code
                        if order.reference_nc:
                            record['reference_nc'] = order.reference_nc

        return res

    def l10n_cr_can_create_document(self, order):
        """ Return a boolean indicating the can create an electronic document.

        :param object order: POS Order
        :rtype: boolean
        """

        # ✅ FIX: NO generar documento (clave/consecutivo) para órdenes en borrador
        # El botón "Orden" deja la orden en draft y el POS igual sincroniza;
        # si aquí no filtramos, se timbra la "precuenta" por error.
        if order.state == 'draft':
            return False

        # if order.refunded_orders_count and not order.reference_nc:
        #     return False

        if order.refunded_order_id and not order.reference_nc:
            return False

        if order.state == 'cancel':
            return False

        return order.config_id.invoice_journal_id.l10n_cr_fiscal_journal

    def l10n_cr_create_document(self, terminal_id, code, reference_nc=None, recreate=False):
        """Crea un documento electronico

            :param char terminal_id: Terminal.
            :param char code: Codigo del tipo de comprobante.
            :param char reference_nc: Origen.
            :param boolean recreate: Recrear.

            :returns: object cedoc
            """

        if not self.document_id or recreate:
            if abs(self.amount_total) == 0.00 or len(self.lines) == 0:
                # Order is amount == 0 and no lines in it,
                # let's not create a CE document for it
                return False

            Document = self.env['ce.document']
            default_document_data = Document.default_get(
                ['state', 'company_id', 'situation', 'ind_state', 'economic_activity_id'])
            if terminal_id.economic_activity_id:
                default_document_data.update(
                    economic_activity_id=terminal_id.economic_activity_id.id,
                )
            voucher_id = self.env['ce.voucher.type'].search([('code', '=', code)])
            l10n_cr_document_number = terminal_id.gen_consecutive_number(voucher_id)
            l10n_cr_document_name = self._l10n_cr_gen_key_numeric(l10n_cr_document_number)
            now = datetime.now(pytz.timezone('America/Costa_Rica'))
            now = now.replace(microsecond=0)
            now = now.strftime(L10N_CR_DATE_FORMAT)
            default_document_data.update(
                order_id=self.id,
                terminal_id=terminal_id.id,
                voucher_type_id=voucher_id.id,
                invoice_type='out_ticket',
                partner_id=self.partner_id.id,
                company_id=self.company_id.id,
                currency_id=self.currency_id.id,
                name=l10n_cr_document_name,
                number=l10n_cr_document_number,
                date_issue=now,
            )
            if code == "03":
                origin_document = self.env["ce.document"].search([('name', '=', reference_nc)])
                if origin_document.voucher_type_code == "04":
                    default_document_data.update(partner_id=False)

            payment_term_type_id = self.env['ce.payment.term.type'].search([('code', '=', '01')], limit=1)
            default_document_data.update({"payment_term_type_id": payment_term_type_id.id})

            doc_id = Document.create(default_document_data)
            doc_id.action_gen_xml(reference_nc=reference_nc)
            self.document_id = doc_id.id
            if self.account_move:
                self.account_move.document_id = doc_id
            return doc_id

    def _l10n_cr_gen_key_numeric(self, number):
        partner_id = self.company_id.partner_id
        tel = partner_id.phone if partner_id.phone else partner_id.mobile
        if not tel:
            raise ValidationError(_('Company does not have a phone defined'))
        if not partner_id.vat:
            raise ValidationError(_('Company does not have a VAT defined'))
        phone = phonenumbers.parse(tel, 'CR')
        country_code = phone.country_code or 506
        now_utc = datetime.now(pytz.timezone('UTC'))
        now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
        dmy = now_cr.strftime("%d%m%y")
        cedula = self.env["ce.document"].get_partner_vat(self.company_id.partner_id)
        security_code = str(random.randint(1, 99999999)).zfill(8)
        situation = '1'  # situation == 'normal'

        return "%s%s%s%s%s%s" % (country_code, dmy, cedula, number, situation, security_code)

    def l10n_cr_invoice_pos_recreate_wizard(self):
        """ Action to open the wizard allowing to recreate a document refused for the selected pos orders.

        :return: An action to open the wizard.
        """
        return {
            'name': _("Recreate Orders"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_cr_invoice_pos.recreate.wizard',
            'target': 'new',
            'context': {'default_pos_order_ids': [Command.set(self.ids)]},
        }

    def _l10n_cr_check_order_for_recreate(self):
        failed_orders = self.filtered(lambda o: o.document_id and o.document_id.ind_state != 'rechazado')
        if failed_orders:
            invoices_str = ", ".join(failed_orders.mapped('name'))
            raise UserError(_("Orders %s only state rechazado.", invoices_str))

        invoices = self
        return invoices

    def _l10n_cr_invoice_pos_recreate_try(self):
        records_sorted = self.sorted('id')
        orders = records_sorted._l10n_cr_check_order_for_recreate()
        if len(orders.company_id) != 1:
            raise UserError(_("You can only process orders sharing the same company."))

        for order in orders:
            order.l10n_cr_action_recreate_document()

    # ===== BUTTONS =====

    def action_send_to_hacienda(self):
        invoices = self._l10n_cr_check_documents_for_send()
        for move in invoices:
            move.document_id.action_send_to_hacienda()

    def action_request_state_to_hacienda(self):
        if self.document_id.xml_file:
            return self.document_id.action_request_state_to_hacienda()
        else:
            raise UserError(_('Must be a xml file.'))

    def l10n_cr_action_recreate_document(self):
        voucher_type_id = self.voucher_type_id
        if not voucher_type_id:
            return False
        if voucher_type_id.code not in [L10N_CR_VOUCHER_TYPE_MAP['FE'], L10N_CR_VOUCHER_TYPE_MAP['TE'], L10N_CR_VOUCHER_TYPE_MAP['NC']]:
            raise UserError("Solo aplica a: FE,TE,NC.")
        if self.document_id and self.document_id.ind_state == 'rechazado':
            """Sustituye factura rechazada por el Ministerio de Hacienda
               y hace referencia al documento actual rechazado"""

            company_id = self.company_id.id
            terminal_id = self.session_id.config_id.terminal_id
            if not terminal_id:
                raise UserError(_("Not found terminal for this TPV."))
            ref_type = self.env['ce.reference.document'].search([('code', '=', '10')], limit=1)
            ref_code = self.env['ce.reference.code'].search([('code', '=', '01')], limit=1)
            ref_doc_vals = {
                'name': 'Sustituye factura rechazada por MH',
                'ref_doctype': ref_type.id,
                'ref_number': self.document_id.name,
                'ref_date': self.document_id.create_date,
                'ref_code': ref_code.id,
                'ref_reason': 'Sustituye factura rechazada por MH',
                'company_id': company_id,
            }
            if self.reference_nc:
                write_status = self.l10n_cr_create_document(terminal_id=terminal_id,
                                                            code=L10N_CR_VOUCHER_TYPE_MAP['NC'],
                                                            reference_nc=self.reference_nc,
                                                            recreate=True,
                                                            )
            else:
                write_status = self.l10n_cr_create_document(terminal_id=terminal_id,
                                                            code=voucher_type_id.code,
                                                            recreate=True,
                                                            )
            if write_status:
                self.document_id.write({'ref_ids': [Command.create(ref_doc_vals)], "is_ref": True})
            return write_status

    def _l10n_cr_check_documents_for_send(self):
        """ Ensure the current records are eligible for sent to Hacienda.

                """
        failed_moves = self.filtered(
            lambda o: (not o.company_id.l10n_cr_auth_user or not o.company_id.l10n_cr_auth_pass)
                      and o.country_code == 'CR')
        if failed_moves:
            invoices_str = ", ".join(failed_moves.mapped('name'))
            raise UserError(_("Invoices %s not selected an interface in a company.", invoices_str))

        invoices = self
        return invoices
