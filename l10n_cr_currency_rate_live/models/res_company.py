# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
import json
import requests
import datetime
import logging
_logger = logging.getLogger(__name__)

CURRENCY_MAPPING_LIST = [{'dolar': 'USD'}, {'euro': 'EUR'}]


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_cr_currency_interval_unit = fields.Selection(
        [
            ("manually", "Manually"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="daily",
        string="Currency Interval",
    )
    l10n_cr_currency_base = fields.Selection(
        [("buyrate", "Buy rate"), ("sellrate", "Sell rate")],
        string="Base",
        default="sellrate",
    )
    l10n_cr_rate_offset = fields.Float("Offset", default=0)
    l10n_cr_currency_next_execution_date = fields.Date(
        string="Following Execution Date"
    )
    l10n_cr_last_currency_sync_date = fields.Date(
        string="Last Sync Date", readonly=True
    )

    def l10n_cr_update_currency_rates(self):

        all_good = True
        for company in self.search([('id', '=', self.env.company.id)]):
            _logger.info("Calling API rates resource.")
            Rate = self.env["res.currency.rate"]

            for a in CURRENCY_MAPPING_LIST:
                for k, v in a.items():
                    currency_id = self.env.ref(
                        "base." + v
                    )
                    if currency_id and currency_id.active:
                        value_api = self.consulta_api(k)
                        if not value_api:
                            _logger.warning(_("No serializable data from API response"))
                            return False

                        inverse_rate = 1 / float(value_api)

                        rate_id = Rate.search(
                            [
                                ("name", "=", fields.Date.today()),
                                ("currency_id", "=", currency_id.id),
                                ("company_id", "=", company.id),
                            ]
                        )
                        if rate_id:
                            rate_id.write({"rate": inverse_rate})
                        else:
                            Rate.create(
                                {
                                    "currency_id": currency_id.id,
                                    "rate": inverse_rate,
                                    "company_id": company.id,
                                }
                            )

                        company.l10n_cr_last_currency_sync_date = fields.Date.today()

        return all_good

    @api.model
    def l10n_cr_run_update_currency(self):

        records = self.search([])
        if records:
            to_update = self.env["res.company"]
            for record in records:
                if record.l10n_cr_currency_interval_unit == "daily":
                    next_update = relativedelta(days=+1)
                elif record.l10n_cr_currency_interval_unit == "weekly":
                    next_update = relativedelta(weeks=+1)
                elif record.l10n_cr_currency_interval_unit == "monthly":
                    next_update = relativedelta(months=+1)
                else:
                    record.l10n_cr_currency_interval_unit = False
                    continue
                record.l10n_cr_currency_next_execution_date = (
                    datetime.date.today() + next_update
                )
                to_update += record

            to_update.l10n_cr_update_currency_rates()

    def consulta_api(self, moneda):
        api_url = self.env["ir.config_parameter"].sudo().get_param("currency.api.url")
        end_point = api_url + str(moneda)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-GPC": "1",
            "Host": "api.hacienda.go.cr",
        }
        try:
            response = requests.get(end_point, headers=headers, timeout=10)
            _logger.warning(response.status_code)
            if response.status_code in (200, 202) and len(response._content) > 0:
                contenido = json.loads(str(response._content, 'utf-8'))

                if moneda == 'dolar':
                    if contenido.get('venta'):
                        venta = contenido.get('venta')
                        cambio_valor = venta['valor']
                        return cambio_valor
                    else:
                        return False
                if moneda == 'euro':
                    if contenido.get('dolares'):
                        cambio_valor = contenido['dolares']
                        return cambio_valor
                    else:
                        return False
            else:
                return False
        except requests.exceptions.ConnectionError as e:
            _logger.warning(_("API requests return the following error %s" % e))
            return False
        except Exception as e:
            _logger.warning(_("API requests return the following error %s" % e))
            return False
