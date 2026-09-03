import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { pick } from "@web/core/utils/objects";
import { formatDateTime } from "@web/core/l10n/dates";
import { parseUTCString } from "@point_of_sale/utils";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    is_cr_country() {
        return this.company.country_id?.code == "CR";
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        if (!this.is_cr_country() || !order) {
            return result;
        }
        result.clave_cr = order.clave_cr;
        result.number = order.number;
        result.reference_nc = order.reference_nc;
        result.voucher_number = order.voucher_number;
        result.partner = order.get_partner();
        return result;
    },
    async pay () {
        let empty_product_cabys_code = this.validate_empty_product_cabys_code();
        if (empty_product_cabys_code) {
            this.dialog.add(AlertDialog, {
                    title: _t("Validation Error"),
                    body: _t("There are products without CABYS."),
                });
            return false;
        }

        await super.pay(...arguments);
    },
    validate_empty_product_cabys_code() {
        const currentOrder = this.get_order();
        let orderlines = currentOrder.get_orderlines();
        const empty_product_cabys_code = orderlines.find(
//            (line) => line.product_id.cabys_code == undefined || line.product_id.cabys_code == false
            (line) => line.product_id.product_cabys_id == undefined || line.product_id.product_cabys_id == false
        );
        return empty_product_cabys_code;
    },
});
