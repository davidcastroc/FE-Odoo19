# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools.misc import xlwt
import logging
import base64
import io

_logger = logging.getLogger(__name__)


class ReportExpenseWizard(models.TransientModel):
    _name = 'l10n_cr_report.details.wizard'
    _description = 'Report Details Wizard'

    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)

    # @api.constrains("start_date", "end_date")
    # def _check_duration(self):
    #     start = self.start_date
    #     end = self.end_date
    #     if start > end:
    #         raise ValidationError("Wrong start date")
    #
    #     today = fields.Date.today()
    #     if start > today:
    #         raise ValidationError("La fecha inicio no puede ser superior al día de hoy")
    #
    #     if end > today:
    #         raise ValidationError("La fecha fin no pude ser superior al día de hoy")

    def generate_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date}
        return self.env.ref('l10n_cr_reports.iva_details_report').report_action([], data=data)

    def action_view(self):
        self.ensure_one()
        date_start = fields.Datetime.from_string(self.start_date)
        date_stop = fields.Datetime.from_string(self.end_date)
        action = self.env.ref("l10n_cr_reports.ecf_document_analysis_action").read()[0]
        domain = [('invoice_date', '>=', date_start), ('invoice_date', '<=', date_stop)]
        if domain:
            action["views"] = [(self.env.ref("l10n_cr_reports.ecf_document_analysis_tree_tree").id, "list")]
            action["domain"] = domain
        else:
            action = {"type": "ir.actions.act_window_close"}

        return action
