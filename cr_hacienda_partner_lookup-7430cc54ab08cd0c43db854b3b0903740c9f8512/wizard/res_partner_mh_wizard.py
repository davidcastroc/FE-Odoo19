# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class ResPartnerMHWizard(models.TransientModel):
    _name = "res.partner.mh.wizard"
    _description = "Resultado consulta Ministerio de Hacienda"

    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto",
        readonly=True
    )

    identification = fields.Char(
        string="Identificación",
        readonly=True
    )

    name = fields.Char(
        string="Nombre en Hacienda",
        readonly=True
    )

    identification_type = fields.Char(
        string="Tipo de identificación",
        readonly=True
    )

    regime = fields.Char(
        string="Régimen",
        readonly=True
    )

    defaulter = fields.Boolean(
        string="Moroso",
        readonly=True
    )

    omitted = fields.Boolean(
        string="Omiso",
        readonly=True
    )

    state = fields.Char(
        string="Estado",
        readonly=True
    )

    tax_administration = fields.Char(
        string="Administración tributaria",
        readonly=True
    )

    activity_ids = fields.One2many(
        "res.partner.mh.activity.wizard",
        "wizard_id",
        string="Actividades económicas",
        readonly=True
    )

    registry_ids = fields.One2many(
        "res.partner.mh.registry.wizard",
        "wizard_id",
        string="Registros especiales",
        readonly=True
    )

    def action_apply_to_partner(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(
                _("No se encontró el contacto asociado a esta consulta.")
            )

        partner = self.partner_id

        values = {}

        # ---------------------------------------------------------
        # Nombre registrado en Hacienda
        # ---------------------------------------------------------
        if self.name:
            values["name"] = self.name.strip()

        # ---------------------------------------------------------
        # Número de identificación fiscal
        # ---------------------------------------------------------
        if self.identification:
            identification = (
                str(self.identification)
                .strip()
                .replace("-", "")
                .replace(" ", "")
            )

            values["vat"] = identification

        # ---------------------------------------------------------
        # Tipo de identificación
        #
        # Hacienda:
        # 01 = Cédula física
        # 02 = Cédula jurídica
        # 03 = DIMEX
        # 04 = NITE
        # 05 = Extranjero
        # ---------------------------------------------------------
        if self.identification_type:
            identification_code = str(
                self.identification_type
            ).strip()

            identification_type = self.env[
                "ce.identification.type"
            ].search(
                [
                    ("code", "=", identification_code),
                ],
                limit=1,
            )

            if not identification_type:
                raise UserError(
                    _(
                        "No se encontró el tipo de identificación "
                        "con código '%s' en Odoo."
                    )
                    % identification_code
                )

            values["identification_id"] = identification_type.id

        # ---------------------------------------------------------
        # Actividad económica
        #
        # En res.partner el campo utilizado por CastroLi-FE es:
        # l10n_cr_activity_id
        #
        # Si Hacienda devuelve varias actividades, utilizamos
        # la primera como actividad principal del contacto.
        # ---------------------------------------------------------
        if self.activity_ids:
            activity_line = self.activity_ids[0]

            activity_code = str(
                activity_line.code or ""
            ).strip()

            activity_name = str(
                activity_line.name or ""
            ).strip()

            if activity_code:
                EconomicActivity = self.env["ce.economic.activity"]

                # Intentamos primero exactamente como viene de Hacienda.
                economic_activity = EconomicActivity.search(
                    [
                        ("code", "=", activity_code),
                    ],
                    limit=1,
                )

                # Algunas respuestas pueden venir como 4772.0
                # mientras que Odoo tenga 4772.
                normalized_code = activity_code

                if not economic_activity and activity_code.endswith(".0"):
                    normalized_code = activity_code[:-2]

                    economic_activity = EconomicActivity.search(
                        [
                            ("code", "=", normalized_code),
                        ],
                        limit=1,
                    )

                # Si no existe en catálogo, se crea con la información
                # devuelta por Hacienda.
                if not economic_activity:
                    economic_activity = EconomicActivity.create(
                        {
                            "code": normalized_code,
                            "name": (
                                activity_name
                                or normalized_code
                            ),
                        }
                    )

                values["l10n_cr_activity_id"] = economic_activity.id

        # ---------------------------------------------------------
        # Aplicar cambios
        # ---------------------------------------------------------
        if not values:
            raise UserError(
                _(
                    "Hacienda no devolvió datos que puedan "
                    "aplicarse al contacto."
                )
            )

        partner.write(values)

        # ---------------------------------------------------------
        # Mostrar notificación y cerrar wizard
        # ---------------------------------------------------------
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Datos actualizados"),
                "message": _(
                    "Los datos de Hacienda fueron aplicados "
                    "correctamente al contacto."
                ),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }


class ResPartnerMHActivityWizard(models.TransientModel):
    _name = "res.partner.mh.activity.wizard"
    _description = "Actividad económica consultada en Hacienda"

    wizard_id = fields.Many2one(
        "res.partner.mh.wizard",
        required=True,
        ondelete="cascade"
    )

    code = fields.Char(
        string="Código",
        readonly=True
    )

    name = fields.Char(
        string="Actividad",
        readonly=True
    )


class ResPartnerMHRegistryWizard(models.TransientModel):
    _name = "res.partner.mh.registry.wizard"
    _description = "Registro especial consultado en Hacienda"

    wizard_id = fields.Many2one(
        "res.partner.mh.wizard",
        required=True,
        ondelete="cascade"
    )

    registry_type = fields.Selection(
        [
            ("mag", "MAG"),
            ("incopesca", "INCOPESCA"),
            ("acuicultores", "Acuicultores"),
        ],
        string="Registro",
        readonly=True
    )

    due_date = fields.Date(
        string="Fecha",
        readonly=True
    )

    active_registry = fields.Boolean(
        string="Activo",
        readonly=True
    )