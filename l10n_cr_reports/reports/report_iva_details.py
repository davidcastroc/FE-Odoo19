# -*- coding: utf-8 -*-
from datetime import timedelta

import pytz

from odoo import api, fields, models, _
from odoo.osv.expression import AND


class ReportIVADetails(models.AbstractModel):

    _name = 'report.l10n_cr_reports.report_ivadetails'
    _description = 'IVA Details'

    def get_invoice_lines(self, economic_activity_id, detailed_type, date_start=False, date_stop=False,
                          move_type=['out_invoice', 'out_refund']):
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC')).replace(tzinfo=None)

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        company_id = self.env.company.id

        domain = [
                  ('invoice_date', '>=', date_start),
                  ('invoice_date', '<=', date_stop),
                  ('move_type', 'in', move_type),
                  ('company_id', '=', company_id),
                  ]
        if economic_activity_id:
            domain = AND([domain, [('economic_activity_id', '=', economic_activity_id)]])

        if detailed_type:
            domain = AND([domain, [('detailed_type_product', '=', detailed_type)]])

        report_iva = self.env["account.report.iva.analysis"].search_read(domain)
        return report_iva

    def get_invoices_exempt(self, detailed_type, identification_type, date_start=False, date_stop=False):
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC')).replace(tzinfo=None)

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        company_id = self.env.company.id

        domain = [
                  ('detailed_type_product', '=', detailed_type),
                  ('invoice_date', '>=', date_start),
                  ('invoice_date', '<=', date_stop),
                  ('move_type', 'in', ['out_invoice', 'out_refund']),
                  ('company_id', '=', company_id),
                  ]

        report_exempt = self.env["account.report.iva.analysis"].search(domain)

        if identification_type == 'internal':
            report_exempt = report_exempt.filtered(
                lambda x: x.partner_id.identification_id.code != '05')
        else:
            report_exempt = report_exempt.filtered(
                lambda x: x.partner_id.identification_id.code == '05')

        return report_exempt

    def get_amount_exoneracion(self, date_start=False, date_stop=False):
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC')).replace(tzinfo=None)

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        company_id = self.env.company.id

        domain = [
                  ('invoice_date', '>=', date_start),
                  ('invoice_date', '<=', date_stop),
                  ('move_type', 'in', ['out_invoice', 'out_refund']),
                  ('fiscal_position_id', '!=', False),
                  ('company_id', '=', company_id),
                  ]
        report_exoneraciones = self.env["account.report.iva.analysis"].search_read(domain)
        amount_total = sum([a['taxed_base_1'] + a['taxed_base_2'] + a['taxed_base_4'] + a['taxed_base_8'] + a['taxed_base_8'] + a['taxed_base_13'] + a['exempt_amount']
                            for a in report_exoneraciones])
        return amount_total

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False):
        """
        """

        # if date_start:
        #     date_start = fields.Datetime.from_string(date_start)
        # else:
        #     # start by default today 00:00:00
        #     user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        #     today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        #     date_start = today.astimezone(pytz.timezone('UTC')).replace(tzinfo=None)
        #
        # if date_stop:
        #     date_stop = fields.Datetime.from_string(date_stop)
        #     # avoid a date_stop smaller than date_start
        #     if (date_stop < date_start):
        #         date_stop = date_start + timedelta(days=1, seconds=-1)
        # else:
        #     # stop by default today 23:59:59
        #     date_stop = date_start + timedelta(days=1, seconds=-1)
        #
        # domain = [
        #           ('invoice_date', '>=', fields.Datetime.to_string(date_start)),
        #           ('invoice_date', '<=', fields.Datetime.to_string(date_stop)),
        #           ('move_type', 'in', ['out_invoice', 'out_refund']),
        #           ]
        # report_iva = self.env["account.report.iva.analysis"].search_read(domain)
        # total_iva = sum([a['taxed_amount_1'] + a['taxed_amount_13'] for a in report_iva])

        economic_activities = self.env.company.l10n_cr_economic_activity_ids

        return {
            'economic_activities': economic_activities,
            'get_invoice_lines': self.get_invoice_lines,
            # 'total_iva': total_iva,
            'get_invoices_exempt': self.get_invoices_exempt,
            'get_amount_exoneracion': self.get_amount_exoneracion,
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        company_currency_id = self.env.company.currency_id

        # initialize data keys with their value if provided, else None
        data.update({
            'date_start': data.get('date_start'),
            'date_stop': data.get('date_stop'),
            'company_currency_id': company_currency_id,
        })
        data.update(self.get_sale_details(data['date_start'], data['date_stop']))
        return data
