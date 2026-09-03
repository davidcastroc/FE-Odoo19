# -*- coding: utf-8 -*-

from odoo import models, fields, api
from collections import defaultdict
from odoo.addons.l10n_cr_invoice.models.account_move_line import L10N_CR_DESCRIPTION_DISCOUNT_TYPE_CODE


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    l10n_cr_discount_type_code = fields.Selection(selection=L10N_CR_DESCRIPTION_DISCOUNT_TYPE_CODE,
                                                  string="Discount Type Code", help="NOTA 20: ANEXOS y ESTRCUTURAS")
    l10n_cr_has_exoneration = fields.Boolean(compute="_compute_l10n_cr_has_exoneration", string="Has Exoneration")
    l10n_cr_partner_exoneration = fields.Many2one("l10n_cr.partner.exoneration",
                                                  compute="_compute_l10n_cr_has_exoneration", string="Exoneration")

    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        res = super()._prepare_invoice_line(**optional_values)
        if self.order_id.country_code == 'CR' and self.l10n_cr_discount_type_code:
            res.update({"l10n_cr_discount_type_code": self.l10n_cr_discount_type_code})

        # if self.order_id.country_code == 'CR' and self.l10n_cr_partner_exoneration:
        #     res.update({"l10n_cr_partner_exoneration": self.l10n_cr_partner_exoneration})

        return res

    @api.depends('order_id.partner_id', 'product_id')
    def _compute_l10n_cr_has_exoneration(self):
        for line in self:
            line.l10n_cr_has_exoneration = False
            line.l10n_cr_partner_exoneration = False
            product_id = line.product_id
            partner_id = line.order_id.partner_id
            if line.order_id.partner_id.l10n_cr_exoneration_authorization and line.product_id and product_id.product_cabys_id:
                for exoneration in partner_id.l10n_cr_exoneration_ids:
                    allowed_cabys = exoneration.allowed_cabys_line_ids
                    if allowed_cabys.filtered(
                        lambda x: x.exoneration_code and x.exoneration_code in product_id.product_cabys_id.code):
                        line.l10n_cr_has_exoneration = True
                        line.l10n_cr_partner_exoneration = exoneration
                # allowed_cabys = line.order_id.partner_id.l10n_cr_exoneration_ids
                # if allowed_cabys.filtered(lambda x: x.exoneration_code and x.exoneration_code in product_id.product_cabys_id.code):
                #     line.l10n_cr_has_exoneration = True

    # extends
    @api.depends('product_id', 'company_id')
    def _compute_tax_id(self):
        if self.order_id.country_code == 'CR':
            lines_by_company = defaultdict(lambda: self.env['sale.order.line'])
            cached_taxes = {}
            for line in self:
                if line.product_type == 'combo':
                    line.tax_id = False
                    continue
                lines_by_company[line.company_id] += line
            for company, lines in lines_by_company.items():
                for line in lines.with_company(company):
                    taxes = None
                    if line.product_id:
                        taxes = line.product_id.taxes_id._filter_taxes_by_company(company)
                    if not line.product_id or not taxes:
                        # Nothing to map
                        line.tax_id = False
                        continue
                    fiscal_position = line.order_id.fiscal_position_id
                    cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                    cache_key += line._get_custom_compute_tax_cache_key()
                    if cache_key in cached_taxes:
                        result = cached_taxes[cache_key]
                    else:
                        if line.order_id.fiscal_position_id and line.l10n_cr_has_exoneration and self.order_id.country_code == 'CR':
                            result = fiscal_position.map_tax(taxes)
                            cached_taxes[cache_key] = result
                        else:
                            # result = fiscal_position.map_tax(taxes)
                            result = taxes
                            cached_taxes[cache_key] = result
                    # If company_id is set, always filter taxes by the company
                    line.tax_id = result

        else:
            return super()._compute_tax_id()
