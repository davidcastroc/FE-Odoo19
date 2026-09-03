# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class Document(models.Model):
    _inherit = "ce.document"

    order_id = fields.Many2one('pos.order', string="Order POS", readonly=True)

    @api.depends('invoice_id', 'order_id')
    def _amount_total(self):
        super(Document, self)._amount_total()
        for env in self:
            if env.order_id:
                env.xml_amount_total = abs(env.order_id.amount_total or 0.0)
                env.xml_amount_tax = abs(env.order_id.amount_tax or 0.0)

    def get_origin_name(self):
        res = super().get_origin_name()
        return self.order_id and self.order_id.name or res

    def _add_reference_information(self, cedoc, classdoc, reference_nc):
        # EXTENDS 'l10n_cr_invoice'

        info_reference = classdoc.InformacionReferenciaType()
        if self.order_id and not self.invoice_id:
            info_reference.set_TipoDoc("04")
            if reference_nc:
                key_numeric_ref = reference_nc
            else:
                key_numeric_ref = self.order_id.pos_order_id.clave_cr
            info_reference.set_Numero(key_numeric_ref)
            date_issue = self.get_time_now_cr()
            info_reference.set_FechaEmision(date_issue)
            info_reference.set_Codigo(self.order_id.reference_code_id.code or "01")
            info_reference.set_Razon("Anulacion")
            cedoc.add_InformacionReferencia(info_reference)
        else:
            super()._add_reference_information(cedoc, classdoc, reference_nc)

    def get_payment_way(self, cedoc=None, classdoc=None):
        # EXTENDS 'l10n_cr_invoice'

        """The sum of all payment "value" must equal the order total.
                Because of this, we add payment methods until we reach the total. The remaining ones cannot be sent."""

        if self.order_id:
            payment_methods = []
            remaining_to_pay = self.xml_amount_total
            for i, pay in enumerate(self.order_id.payment_ids.filtered(lambda payment: not payment.is_change), 1):
                if remaining_to_pay <= 0:
                    break
                if pay.payment_method_id.l10n_cr_payment_method_id:
                    payment_method_code = pay.payment_method_id.l10n_cr_payment_method_id.code
                    payment_way = classdoc.MedioPago(TipoMedioPago=payment_method_code,
                                                     TotalMedioPago=abs(min(remaining_to_pay, pay.amount)))
                    if payment_method_code == '99':
                        payment_way.set_MedioPagoOtros(self.limit(pay.payment_method_id.name, 100))

                    payment_methods.append(payment_way)
                else:
                    payment_way = classdoc.MedioPago(TipoMedioPago="99",
                                                     TotalMedioPago=abs(min(remaining_to_pay, pay.amount)))
                    payment_way.set_MedioPagoOtros(self.limit(pay.payment_method_id.name, 100))
                    payment_methods.append(payment_way)

                remaining_to_pay = self.currency_id.round(remaining_to_pay - pay.amount)
                if i >= 4:
                    break

            return payment_methods
        else:
            return super().get_payment_way(cedoc, classdoc)
