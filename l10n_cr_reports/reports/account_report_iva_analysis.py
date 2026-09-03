# -*- coding: utf-8 -*-

from odoo import fields, models, tools, api, _
from collections import defaultdict
# from odoo.osv import expression


class IVAAnalysis(models.Model):
    """ IVA Analysis """

    _name = "account.report.iva.analysis"
    _auto = False
    _description = "Report IVA Analysis"
    _order = 'invoice_date desc, id desc'

    id = fields.Integer()
    name = fields.Char()
    move_id = fields.Many2one("account.move")
    line_id = fields.Many2one("account.move.line")
    detailed_type_product = fields.Selection([('consu', 'Bienes'), ('service', "Servicios")])
    partner_id = fields.Many2one("res.partner")
    economic_activity_id = fields.Many2one("ce.economic.activity")
    move_type = fields.Char()
    state = fields.Char()
    invoice_date = fields.Date()
    fiscal_position_id = fields.Many2one("account.fiscal.position")
    currency_id = fields.Many2one("res.currency")
    company_id = fields.Many2one("res.company")
    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True,
    )

    taxed_base_05 = fields.Float(compute="_compute_taxes")
    taxed_amount_05 = fields.Float(compute="_compute_taxes")
    taxed_base_1 = fields.Float(compute="_compute_taxes")
    taxed_amount_1 = fields.Float(compute="_compute_taxes")
    taxed_base_2 = fields.Float(compute="_compute_taxes")
    taxed_amount_2 = fields.Float(compute="_compute_taxes")
    taxed_base_4 = fields.Float(compute="_compute_taxes")
    taxed_amount_4 = fields.Float(compute="_compute_taxes")
    taxed_base_8 = fields.Float(compute="_compute_taxes")
    taxed_amount_8 = fields.Float(compute="_compute_taxes")
    taxed_base_13 = fields.Float(compute="_compute_taxes")
    taxed_amount_13 = fields.Float(compute="_compute_taxes")
    exempt_amount = fields.Float(compute="_compute_taxes")

    def _compute_taxes(self):
        for rec in self:
            tax_data = rec.get_taxed_amount_data(rec.line_id)

            rec.taxed_base_1 = tax_data['02_taxed_base']
            rec.taxed_amount_1 = tax_data['02_taxed_amount']
            rec.taxed_base_2 = tax_data['03_taxed_base']
            rec.taxed_amount_2 = tax_data['03_taxed_amount']
            rec.taxed_base_4 = tax_data['04_taxed_base']
            rec.taxed_amount_4 = tax_data['04_taxed_amount']
            rec.taxed_base_8 = tax_data['07_taxed_base']
            rec.taxed_amount_8 = tax_data['07_taxed_amount']
            rec.taxed_base_13 = tax_data['08_taxed_base']
            rec.taxed_amount_13 = tax_data['08_taxed_amount']
            rec.taxed_base_05 = tax_data['09_taxed_base']
            rec.taxed_amount_05 = tax_data['09_taxed_amount']
            rec.exempt_amount = tax_data['exempt_amount']

    def get_taxed_amount_data(self, lines):
        """Invoice amounts related values.

        Código del impuesto la tarifa del impuesto, Nota #8
        01 IVA
        02 Impuesto Selectivo de Consumo
        03 Impuesto Unico a los Combustibles
        04 Impuesto específico de Bebidas Alcoholicas
        05 Impuesto especifico sobre las bebidas envasadas sin contenido alcoholico y jabones de tocador
        06 Impuesto a los productos de tabaco
        07 IVA (calculo especial)
        08 IVA Regimen de Bienes Usados (Factor)
        12 Impuesto especifico al cemento
        99 Otros

        Código de la tarifa del IVA
        01 Tarifa 0% (Exento)
        02 Tarifa Reducida 1%
        03 Tarifa reducida 2%
        04 Tarifa reducida 4%
        05 Transitorio 0%
        06 Transitorio 4%
        07 Transitorio 8%
        08 Tarifa General 13%
        09 Tarifa reducida 0.5%

        :param list lines: Lines of document.
        """

        iva_data = {
            "total_taxed_amount": 0,
            "02_taxed_base": 0,
            "03_taxed_base": 0,
            "04_taxed_base": 0,
            "05_taxed_base": 0,
            "06_taxed_base": 0,
            "07_taxed_base": 0,
            "08_taxed_base": 0,
            "09_taxed_base": 0,

            "02_taxed_amount": 0,
            "03_taxed_amount": 0,
            "04_taxed_amount": 0,
            "05_taxed_amount": 0,
            "06_taxed_amount": 0,
            "07_taxed_amount": 0,
            "08_taxed_amount": 0,
            "09_taxed_amount": 0,
            "exempt_amount": 0,
        }

        tax_data = [
            line.tax_ids.compute_all(
                price_unit=line.price_subtotal,
                currency=line.currency_id,
                product=line.product_id,
                partner=self.partner_id,
                handle_price_include=False,
            )
            for line in lines
        ]

        iva_data["total_taxed_amount"] = sum(
            line["total_excluded"] for line in tax_data
        )

        for line_taxes in tax_data:
            for tax in line_taxes["taxes"]:
                if not tax["amount"]:
                    iva_data["exempt_amount"] += self._convert_to_local_currency(tax["base"])

                tax_id = self.env["account.tax"].browse(tax["id"])
                if tax_id.iva_tax_rate == '02':
                    iva_data["02_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["02_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '03':
                    iva_data["03_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["03_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '04':
                    iva_data["04_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["04_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '05':
                    iva_data["05_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["05_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '06':
                    iva_data["06_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["06_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '07':
                    iva_data["07_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["07_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["07_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '08':
                    iva_data["08_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["08_taxed_amount"] += self._convert_to_local_currency(tax["amount"])
                if tax_id.iva_tax_rate == '09':
                    iva_data["09_taxed_base"] += self._convert_to_local_currency(tax["base"])
                    iva_data["09_taxed_amount"] += self._convert_to_local_currency(tax["amount"])

        return iva_data

    def _convert_to_local_currency(self, amount):
        sign = -1 if self.move_type in ['in_refund', 'out_refund'] else 1
        amount = self.currency_id._convert(
            amount, self.company_id.currency_id, self.company_id, self.invoice_date or fields.Date.context_today(self)
        )
        return amount * sign

    @api.model
    def get_activity_data(self, measure="", domain=[]):
        company_id = self.env.company
        activities = self.env["ce.economic.activity"].search([('id', 'in', company_id.l10n_cr_economic_activity_ids.ids)])
        tuple_taxes = ('taxed_base_05', 'taxed_amount_05', 'taxed_base_1', 'taxed_amount_1', 'taxed_base_2',
                       'taxed_amount_2', 'taxed_base_4', 'taxed_amount_4', 'taxed_base_8', 'taxed_amount_8',
                       'taxed_base_13', 'taxed_amount_13', 'exempt_amount')

        if measure:
            domain = domain + [('economic_activity_id', '=', int(measure))]
            # domain = expression.AND([
            #     domain,
            #     [('economic_activity_id', '=', int(measure))]
            # ])

        sales_iva_consu = self.search_read(domain + [('detailed_type_product', '=', 'consu')])
        # sales_iva_consu = self.search_read(expression.AND([domain, [('detailed_type_product', '=', 'consu')]]))
        # dict_sales_iva_consu = {}
        result = defaultdict(int)
        for dic in sales_iva_consu:
            for key, value in dic.items():
                if key in tuple_taxes:
                    result[key] += value

        sales_iva_service = self.search_read(domain + [('detailed_type_product', '=', 'service')])
        # dict_sales_iva_consu = {}
        result1 = defaultdict(int)
        for dic in sales_iva_service:
            for key, value in dic.items():
                if key in tuple_taxes:
                    result1[key] += value

        economic_activities = [{
                'id': a.id,
                'name': a.name,
                'activity_selected': a.id == activities[0].id,

            } for a in activities]

        taxes_scope = [{"id": "consu", "name": "Bienes"},
                       {"id": "service", "name": "Servicios"}]

        return {
            'dict_sales_iva_consu': result,
            'dict_sales_iva_service': result1,
            'economic_activities': economic_activities,
            'taxes_scope': taxes_scope,
            # 'company_currency_symbol': f"{company_id.currency_id.symbol} ",
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""CREATE or REPLACE VIEW {self._table} as
                SELECT 
                ml.id as id,
                am.l10n_cr_document_number as name,
                
                ml.move_id,
                ml.id as line_id,
                am.partner_id,
                am.economic_activity_id,
                am.move_type,
                am.state,
                am.invoice_date,
                am.fiscal_position_id,
                am.company_id,
                am.currency_id,
                COALESCE(act.tax_scope, 'consu') as detailed_type_product

                FROM account_move am
                INNER JOIN account_move_line ml ON (ml.move_id = am.id)
                INNER JOIN account_move_line_account_tax_rel rel ON (rel.account_move_line_id = ml.id)
                INNER JOIN account_tax act ON (rel.account_tax_id = act.id)

                WHERE state = 'posted'
                AND move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
                AND act.iva_tax_rate in ('01', '02', '03', '04', '05', '06', '07', '08', '09')
                """)
