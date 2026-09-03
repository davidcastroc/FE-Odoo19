# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Document(models.Model):
    _inherit = "ce.document"

    def set_additional_vals(self, cedoc, classdoc, *args):
        """Set additional values to the item.

        :param cedoc: Instancia del Elemento raiz.
        :param classdoc: Clase del tipo de documento.
        :param args: Additional arguments.
        """

        super().set_additional_vals(cedoc, classdoc, *args)

        if self.invoice_id:
            salesman_number = self.invoice_id.l10n_cr_salesman_number
            order_number = self.invoice_id.l10n_cr_order_number or ""
            delivery_date = self.invoice_id.l10n_cr_delivery_date and self.invoice_id.l10n_cr_delivery_date.strftime('%Y-%m-%d')
            reception_number = self.invoice_id.l10n_cr_reception_number
            pv_number = self.invoice_id.l10n_cr_pv_number
        else:
            salesman_number = ""
            order_number = ""
            delivery_date = ""
            reception_number = ""
            pv_number = ""

        other = classdoc.OtrosType()
        if salesman_number:
            other_text = classdoc.OtroTextoType(codigo="NumeroVendedor", valueOf_=salesman_number)
            other.add_OtroTexto(other_text)
        if order_number:
            other_text2 = classdoc.OtroTextoType(codigo="NumeroOrden", valueOf_=order_number)
            other.add_OtroTexto(other_text2)
        if pv_number:
            other_text3 = classdoc.OtroTextoType(codigo="EnviarGLN", valueOf_=pv_number)
            other.add_OtroTexto(other_text3)
        if delivery_date:
            other_text4 = classdoc.OtroTextoType(codigo="FechaOrden", valueOf_=delivery_date)
            other.add_OtroTexto(other_text4)
        if reception_number:
            other_text5 = classdoc.OtroTextoType(codigo="NumeroRecepcion", valueOf_=reception_number)
            other.add_OtroTexto(other_text5)
        cedoc.set_Otros(other)
