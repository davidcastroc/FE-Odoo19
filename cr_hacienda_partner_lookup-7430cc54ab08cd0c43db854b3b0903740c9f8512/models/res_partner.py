# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _mh_normalize_identification(self, identification):
        """Hacienda espera la identificación sin espacios ni guiones."""
        return (identification or "").replace("-", "").replace(" ", "").strip()

    def _mh_parse_date(self, value):
        if not value:
            return False
        for date_format in ("%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, date_format).date()
            except (TypeError, ValueError):
                continue
        return False

    def _consult_res_partner_mh(self, identification=None, raise_error=True):
        self.ensure_one()
        identification = self._mh_normalize_identification(identification or self.vat)
        if not identification:
            if raise_error:
                raise UserError(_("Por favor ingrese una cédula/identificación en el campo Número de identificación fiscal (Tax ID) del contacto."))
            return False

        url = "https://api.hacienda.go.cr/fe/ae"
        try:
            response = requests.get(
                url,
                params={"identificacion": identification},
                timeout=20,
            )
        except requests.RequestException as exc:
            _logger.exception("Error consultando Ministerio de Hacienda para %s", identification)
            if raise_error:
                raise UserError(_(
                    "No fue posible conectarse con el servicio del Ministerio de Hacienda. "
                    "Intente nuevamente más tarde.\n\nDetalle técnico: %s"
                ) % exc)
            return False

        if response.status_code == 404:
            if raise_error:
                raise UserError(_("Contacto no encontrado en la base de datos de Hacienda. Identificación: %s") % identification)
            return False

        if response.status_code != 200:
            _logger.warning(
                "Hacienda respondió HTTP %s para %s: %s",
                response.status_code,
                identification,
                response.text[:1000],
            )
            if raise_error:
                raise UserError(_(
                    "El Ministerio de Hacienda respondió con un error (HTTP %s). "
                    "Intente nuevamente más tarde."
                ) % response.status_code)
            return False

        try:
            return response.json()
        except ValueError:
            _logger.warning("Respuesta no JSON de Hacienda para %s: %s", identification, response.text[:1000])
            if raise_error:
                raise UserError(_("Hacienda respondió con un formato no válido."))
            return False

    def action_consult_res_partner(self):
        self.ensure_one()
        identification = self._mh_normalize_identification(self.vat)
        if not identification:
            raise UserError(_("Por favor ingrese una cédula/identificación en el campo Número de identificación fiscal (Tax ID) del contacto."))

        response = self._consult_res_partner_mh(identification=identification)
        tax_situation = response.get("situacionTributaria") or response
        situation = tax_situation.get("situacion") or {}
        regime = tax_situation.get("regimen") or {}

        if isinstance(regime, dict):
            regime_description = regime.get("descripcion") or regime.get("nombre") or ""
        else:
            regime_description = str(regime or "")

        wizard = self.env["res.partner.mh.wizard"].create({
            "partner_id": self.id,
            "identification": identification,
            "name": tax_situation.get("nombre") or "",
            "identification_type": str(tax_situation.get("tipoIdentificacion") or ""),
            "regime": regime_description,
            "defaulter": bool(situation.get("moroso")),
            "omitted": bool(situation.get("omiso")),
            "state": str(situation.get("estado") or ""),
            "tax_administration": str(situation.get("administracionTributaria") or ""),
        })

        activity_commands = []
        for activity in tax_situation.get("actividades") or []:
            raw_code = str(activity.get("codigo") or "")
            code = raw_code.zfill(6) if raw_code else ""
            activity_commands.append((0, 0, {
                "code": code,
                "name": str(activity.get("descripcion") or ""),
            }))
        if activity_commands:
            wizard.write({"activity_ids": activity_commands})

        registry_commands = []
        for item in response.get("listaDatosMAG") or []:
            registry_commands.append((0, 0, {
                "registry_type": "mag",
                "due_date": self._mh_parse_date(item.get("fechaBajaMAG")),
                "active_registry": bool(item.get("indicadorActivoMAG")),
            }))
        for item in response.get("listaDatosIncopesca") or []:
            registry_commands.append((0, 0, {
                "registry_type": "incopesca",
                "due_date": self._mh_parse_date(item.get("fechaVenceIncopesca")),
                "active_registry": bool(item.get("indicadorActivoIncopesca")),
            }))
        for item in response.get("listaDatosAcuicultores") or []:
            registry_commands.append((0, 0, {
                "registry_type": "acuicultores",
                "due_date": self._mh_parse_date(item.get("fechaVenceAcuicultor")),
                "active_registry": bool(item.get("indicadorActivoAcuicultor")),
            }))
        if registry_commands:
            wizard.write({"registry_ids": registry_commands})

        return {
            "name": _("Resultado consulta Ministerio de Hacienda"),
            "type": "ir.actions.act_window",
            "res_model": "res.partner.mh.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
