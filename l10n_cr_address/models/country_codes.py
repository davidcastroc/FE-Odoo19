# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCountryCounty(models.Model):
    _name = "res.country.county"
    _description = "Country County"

    code = fields.Char(string="Código")
    state_id = fields.Many2one(comodel_name="res.country.state", string="Province")
    name = fields.Char(string="Nombre")


class ResCountryDistrict(models.Model):
    _name = "res.country.district"
    _description = "Country District"

    code = fields.Char(string="Código")
    county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón")
    name = fields.Char(string="Nombre")


class ResCountryNeighborhood(models.Model):
    _name = "res.country.neighborhood"
    _description = "Country Neighborhood"

    code = fields.Char(string="Código")
    district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito")
    name = fields.Char(string="Nombre")
