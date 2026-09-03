# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    alias_auto_extract_xml_only = fields.Boolean(
        string='Auto extract XMLs only',
        help='Only extract XML files attached to email arriving trough this email alias.',
    )
