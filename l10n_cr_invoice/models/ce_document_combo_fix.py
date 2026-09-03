# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import ValidationError
from collections import defaultdict

class CeDocument(models.Model):
    _inherit = "ce.document"

    _PARENT_FIELDS = (
        "combo_parent_id",
        "combo_parent_line_id",
        "parent_combo_line_id",
        "combo_parent",
        "parent_line_id",
        "parent_id",
    )

    # -----------------------------
    # Helpers: jerarquía
    # -----------------------------
    def _get_combo_parent(self, line):
        for f in self._PARENT_FIELDS:
            if hasattr(line, f):
                p = getattr(line, f)
                if p:
                    return p
        return False

    def _get_combo_children(self, lines, parent_line):
        children = []
        for l in lines:
            p = self._get_combo_parent(l)
            if p and getattr(p, "id", False) == parent_line.id:
                children.append(l)
        return children

    # -----------------------------
    # Helpers: impuestos / indicador
    # -----------------------------
    def _line_taxes(self, line):
        # POS: tax_ids_after_fiscal_position, Invoice: tax_ids
        if hasattr(line, "tax_ids_after_fiscal_position") and line.tax_ids_after_fiscal_position:
            return line.tax_ids_after_fiscal_position
        if hasattr(line, "tax_ids") and line.tax_ids:
            return line.tax_ids
        return self.env["account.tax"]

    def _line_indicator_prod_service(self, line):
        """
        1 = Mercancía / Bien
        2 = Servicio
        """
        taxes = self._line_taxes(line)
        iva = taxes.filtered(lambda t: t.iva_tax_rate in ["01","02","03","04","05","06","07","08","09","10"])
        if iva:
            return 2 if any(t.tax_scope == "service" for t in iva) else 1

        prod = line.product_id
        detailed_type = getattr(prod, "detailed_type", False) or getattr(prod.product_tmpl_id, "detailed_type", False)
        if detailed_type:
            return 2 if detailed_type == "service" else 1

        return 2 if getattr(prod, "type", "") == "service" else 1

    def _combo_is_mixed(self, child_lines):
        indicators = set(self._line_indicator_prod_service(l) for l in child_lines)
        return len(indicators) > 1

    def _r5(self, x):
        return round(float(x or 0.0), 5)

    # ======================================================
    # 1) DECIDIR qué líneas van al XML (la clave de todo)
    # ======================================================
    def _iterable_products_xml(self, lines):
        """
        Reglas:
        - Si NO es POS -> no tocamos
        - POS combos:
          * combo MIXTO -> exporta HIJOS como líneas normales (PADRE NO VIAJA)
          * combo NO MIXTO -> exporta PADRE como línea normal (HIJOS NO VIAJAN)
        """
        self.ensure_one()

        if not getattr(self, "order_id", False):
            return lines

        try:
            all_lines = list(lines)
        except Exception:
            return lines

        # Mapear hijos por parent.id
        children_by_parent = defaultdict(list)
        for l in all_lines:
            p = self._get_combo_parent(l)
            if p and getattr(p, "id", False):
                children_by_parent[p.id].append(l)

        out = []
        for l in all_lines:
            p = self._get_combo_parent(l)

            # Si es HIJO:
            if p and getattr(p, "id", False):
                childs = children_by_parent.get(p.id, [])
                if self._combo_is_mixed(childs):
                    # MIXTO -> hijo viaja como línea normal
                    out.append(l)
                # NO MIXTO -> hijo NO viaja (va dentro del surtido)
                continue

            # Si es PADRE con hijos:
            childs = children_by_parent.get(getattr(l, "id", 0), [])
            if childs:
                if self._combo_is_mixed(childs):
                    # MIXTO -> padre NO viaja
                    continue
                # NO MIXTO -> padre sí viaja
                out.append(l)
                continue

            # Línea normal
            out.append(l)

        return out

    # ======================================================
    # 2) DetalleSurtido SOLO para combos NO mixtos
    # ======================================================
    def _gen_surtido_detail(self, line, item, cedoc, classdoc):
        """
        Firma EXACTA: (line, item, cedoc, classdoc)
        """
        self.ensure_one()

        if not getattr(self, "order_id", False):
            return super()._gen_surtido_detail(line, item, cedoc, classdoc)

        all_lines = list(self.order_id.lines)
        child_lines = self._get_combo_children(all_lines, line)
        if not child_lines:
            return super()._gen_surtido_detail(line, item, cedoc, classdoc)

        # Si es mixto, NO generamos surtido (y en teoría el padre no debería viajar)
        if self._combo_is_mixed(child_lines):
            return None

        detail_surtido = classdoc.DetalleSurtido()

        for cl in child_lines:
            prod = cl.product_id
            qty = cl.qty if hasattr(cl, "qty") else cl.quantity
            qty = abs(qty or 0.0) or 1.0

            # Precio unitario sin impuestos
            pu_untaxed = abs(self._construct_tax_excluded(cl.price_unit, cl))
            pu_untaxed = self._r5(pu_untaxed)

            disc = float(getattr(cl, "discount", 0.0) or 0.0)
            base = self._r5(pu_untaxed * qty)
            disc_amount = self._r5(base * (disc / 100.0))
            subtotal = self._r5(base - disc_amount)

            cabys = (prod.product_cabys_id.code if getattr(prod, "product_cabys_id", False) and prod.product_cabys_id.code else "0000000000000")
            uom_code = "Unid"
            if getattr(cl, "product_uom_id", False) and cl.product_uom_id.code:
                uom_code = cl.product_uom_id.code
            elif getattr(prod, "uom_id", False) and prod.uom_id.code:
                uom_code = prod.uom_id.code

            surt_line = classdoc.LineaDetalleSurtido(
                CodigoCABYSSurtido=cabys,
                CantidadSurtido=qty,
                UnidadMedidaSurtido=uom_code,
                DetalleSurtido=prod.display_name,
                PrecioUnitarioSurtido=pu_untaxed,
            )
            surt_line.set_MontoTotalSurtido(base)
            surt_line.set_SubTotalSurtido(subtotal)
            surt_line.set_BaseImponibleSurtido(subtotal)

            taxes = self._line_taxes(cl).filtered(lambda t: t.iva_tax_rate in ["01","02","03","04","05","06","07","08","09","10"])
            for t in taxes:
                if not t.code_cr:
                    raise ValidationError("Impuesto sin code_cr en componente de combo: %s" % t.display_name)

                rate = float(t.amount or 0.0)
                monto = self._r5(subtotal * rate / 100.0)

                imp_surt = classdoc.ImpuestoSurtido(
                    CodigoImpuestoSurtido=t.code_cr,
                    CodigoTarifaIVASurtido=(t.iva_tax_rate or "08"),
                    TarifaSurtido=rate,
                    MontoImpuestoSurtido=abs(monto),
                )
                surt_line.add_ImpuestoSurtido(imp_surt)

            detail_surtido.add_LineaDetalleSurtido(surt_line)

        return detail_surtido

    # ======================================================
    # 3) Recalcular padre combo (NO mixto) para cuadrar Hacienda
    # ======================================================
    def _compute_combo_from_children(self, parent_line, child_lines):
        """
        Retorna:
        - pu_parent_untaxed
        - subtotal_total (suma subtotales hijos)
        - impuesto_map: {(code_cr, iva_rate, indicator): amount_total}
        """
        parent_qty = parent_line.qty if hasattr(parent_line, "qty") else parent_line.quantity
        parent_qty = abs(parent_qty or 0.0) or 1.0

        subtotal_total = 0.0
        impuesto_map = defaultdict(float)

        for cl in child_lines:
            qty = cl.qty if hasattr(cl, "qty") else cl.quantity
            qty = abs(qty or 0.0) or 1.0

            pu_untaxed = abs(self._construct_tax_excluded(cl.price_unit, cl))
            pu_untaxed = self._r5(pu_untaxed)

            disc = float(getattr(cl, "discount", 0.0) or 0.0)
            base = self._r5(pu_untaxed * qty)
            disc_amount = self._r5(base * (disc / 100.0))
            subtotal = self._r5(base - disc_amount)

            subtotal_total += subtotal

            taxes = self._line_taxes(cl).filtered(lambda t: t.iva_tax_rate in ["01","02","03","04","05","06","07","08","09","10"])
            for t in taxes:
                if not t.code_cr:
                    raise ValidationError("Impuesto sin code_cr en componente de combo: %s" % t.display_name)

                rate = float(t.amount or 0.0)
                monto = self._r5(subtotal * rate / 100.0)
                indicator = 2 if getattr(t, "tax_scope", "") == "service" else 1
                impuesto_map[(t.code_cr, t.iva_tax_rate or "08", indicator, rate)] += monto

        pu_parent_untaxed = self._r5(subtotal_total / parent_qty)
        return pu_parent_untaxed, self._r5(subtotal_total), impuesto_map

    # ======================================================
    # 4) Hook fuerte: post-fix + resumen + desglose + medio pago
    # ======================================================
    def _gen_detail_and_summary(self, cedoc, classdoc):
        self.ensure_one()

        res = super()._gen_detail_and_summary(cedoc, classdoc)

        # Solo POS
        if not getattr(self, "order_id", False):
            return res

        all_lines = list(self.order_id.lines)

        # children_by_parent
        children_by_parent = defaultdict(list)
        for l in all_lines:
            p = self._get_combo_parent(l)
            if p and getattr(p, "id", False):
                children_by_parent[p.id].append(l)

        # XML lines
        try:
            detail = res.get_DetalleServicio()
            xml_lines = detail.get_LineaDetalle() or []
        except Exception:
            return res

        # ---- A) Arreglar combos NO mixtos (padre + surtido) ----
        for dl in xml_lines:
            try:
                det = dl.get_Detalle()
                qty_xml = float(dl.get_Cantidad() or 0.0)

                # encontrar parent_line que esté en XML (NO hijo)
                parent_line = None
                for l in all_lines:
                    if self._get_combo_parent(l):
                        continue
                    # match por nombre
                    if l.product_id and (getattr(l, "full_product_name", "") == det or l.product_id.display_name == det or l.product_id.name == det):
                        q = float((l.qty if hasattr(l, "qty") else l.quantity) or 0.0)
                        if abs(q - qty_xml) < 0.00001:
                            # debe tener hijos
                            if children_by_parent.get(l.id):
                                parent_line = l
                                break

                if not parent_line:
                    continue

                childs = children_by_parent.get(parent_line.id, [])
                if not childs:
                    continue

                # si es MIXTO, este padre NO debería estar en XML por _iterable_products_xml
                if self._combo_is_mixed(childs):
                    continue

                # asegurar surtido real
                surt = self._gen_surtido_detail(parent_line, dl, res, classdoc)
                if surt:
                    dl.set_DetalleSurtido(surt)

                pu_parent, subtotal_total, impuesto_map = self._compute_combo_from_children(parent_line, childs)

                qty = float(dl.get_Cantidad() or 0.0) or 1.0

                # Precio/montos para -150/-516
                dl.set_PrecioUnitario(abs(pu_parent))
                dl.set_MontoTotal(abs(self._r5(pu_parent * qty)))
                dl.set_SubTotal(abs(self._r5(pu_parent * qty)))
                if hasattr(dl, "set_BaseImponible"):
                    dl.set_BaseImponible(dl.get_SubTotal())

                # Rehacer impuestos del padre = suma hijos (para -496/-488/-54)
                # OJO: algunos generateds no permiten "set_Impuesto([])", entonces lo hacemos best-effort:
                try:
                    if hasattr(dl, "set_Impuesto"):
                        dl.set_Impuesto([])
                except Exception:
                    pass

                impuesto_neto = 0.0
                for (code_cr, iva_rate, indicator, rate), monto in impuesto_map.items():
                    imp = classdoc.ImpuestoType(
                        Codigo=code_cr,
                        Tarifa=rate,
                        indicator_prod_service=indicator,
                    )
                    if code_cr in ["01", "07"]:
                        imp.set_CodigoTarifaIVA(iva_rate or "08")
                    imp.set_Monto(abs(monto))
                    dl.add_Impuesto(imp)
                    impuesto_neto += float(monto or 0.0)

                if hasattr(dl, "set_ImpuestoNeto") and self.voucher_type_code != "09":
                    dl.set_ImpuestoNeto(abs(self._r5(impuesto_neto)))

                dl.set_MontoTotalLinea(abs(self._r5((dl.get_SubTotal() or 0.0) + impuesto_neto)))

            except Exception:
                continue

        # ---- B) Recalcular Resumen + Desglose a partir de lo que quedó en xml_lines ----
        try:
            summary = res.get_ResumenFactura()

            total_serv_grav = 0.0
            total_serv_exe = 0.0
            total_mer_grav = 0.0
            total_mer_exe = 0.0
            total_impuesto = 0.0

            breakdown = defaultdict(float)

            for dl in xml_lines:
                sub = float(dl.get_SubTotal() or 0.0)

                impuestos = []
                try:
                    impuestos = dl.get_Impuesto() or []
                except Exception:
                    impuestos = []

                if not impuestos:
                    # sin impuestos: lo tratamos como exento (mercancía por seguridad)
                    total_mer_exe += sub
                    continue

                # tipo dominante por indicator de los impuestos
                ind = None
                for tax in impuestos:
                    try:
                        ind = tax.indicator_prod_service
                        break
                    except Exception:
                        ind = None

                line_tax_total = 0.0
                for tax in impuestos:
                    code = tax.get_Codigo()
                    iva_rate = tax.get_CodigoTarifaIVA()
                    monto = float(tax.get_Monto() or 0.0)
                    line_tax_total += monto
                    breakdown[(code, iva_rate)] += monto

                total_impuesto += line_tax_total

                if ind == 2:
                    total_serv_grav += sub
                else:
                    total_mer_grav += sub

            summary.set_TotalServGravados(abs(self._r5(total_serv_grav)))
            summary.set_TotalServExentos(abs(self._r5(total_serv_exe)))
            summary.set_TotalMercanciasGravadas(abs(self._r5(total_mer_grav)))
            summary.set_TotalMercanciasExentas(abs(self._r5(total_mer_exe)))

            summary.set_TotalGravado(abs(self._r5(total_serv_grav + total_mer_grav)))
            summary.set_TotalExento(abs(self._r5(total_serv_exe + total_mer_exe)))

            total_venta = float(summary.get_TotalGravado()) + float(summary.get_TotalExento())
            if hasattr(summary, "get_TotalExonerado"):
                total_venta += float(summary.get_TotalExonerado() or 0.0)
            summary.set_TotalVenta(abs(self._r5(total_venta)))

            # Limpiar desglose previo si se puede
            try:
                if hasattr(summary, "set_TotalDesgloseImpuesto"):
                    summary.set_TotalDesgloseImpuesto([])
            except Exception:
                pass

            for (code, iva_rate), amount in breakdown.items():
                total_desglose = classdoc.TotalDesgloseImpuesto(
                    Codigo=code,
                    CodigoTarifaIVA=iva_rate,
                    TotalMontoImpuesto=abs(self._r5(amount)),
                )
                summary.add_TotalDesgloseImpuesto(total_desglose)

            summary.set_TotalImpuesto(abs(self._r5(total_impuesto)))

            descuentos = float(summary.get_TotalDescuentos() or 0.0) if hasattr(summary, "get_TotalDescuentos") else 0.0
            summary.set_TotalVentaNeta(abs(self._r5(float(summary.get_TotalVenta()) - descuentos)))

            otros = float(summary.get_TotalOtrosCargos() or 0.0) if hasattr(summary, "get_TotalOtrosCargos") else 0.0
            summary.set_TotalComprobante(abs(self._r5(float(summary.get_TotalVentaNeta()) + float(summary.get_TotalImpuesto()) + otros)))

            res.set_ResumenFactura(summary)
        except Exception:
            pass

        # ---- C) MedioPago en TE/POS (evita -517) ----
        try:
            # Si ya lo trae, no lo tocamos.
            summ = res.get_ResumenFactura()
            has_mp = False
            try:
                mp = summ.get_MedioPago()
                has_mp = bool(mp)
            except Exception:
                has_mp = False

            if not has_mp:
                # Consolidado simple: efectivo (01) por el total
                total = float(getattr(self.order_id, "amount_total", 0.0) or 0.0)
                summ.set_MedioPago([classdoc.MedioPago(TipoMedioPago="01", TotalMedioPago=abs(total))])
                res.set_ResumenFactura(summ)
        except Exception:
            pass

        return res
