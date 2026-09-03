import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";


patch(PosOrder.prototype, {
    is_cr_country() {
        return this.company.country_id?.code === "CR";
    },
    export_for_printing(baseUrl, headerData) {
        let result = super.export_for_printing(...arguments);
        if (!this.is_cr_country()){
            return result;
        }
//        result.partner = self.get_partner();
        result.clave_cr = this.clave_cr;
        result.number = this.number;
        result.reference_nc = this.reference_nc;
        result.voucher_number = this.voucher_number;
        result.QR_code = this.QR_code;
        return result;
    },
    wait_for_push_order() {
        var result = super.wait_for_push_order(...arguments);
        result = Boolean(result || this.is_cr_country());
        return result;
    },
    isFactura() {
        let partner = this.get_partner();
        if (!partner){
            return false
        }

        if (!partner.identification_id){
            return false;
        }

        if ((partner.identification_id && partner.identification_id.code != "02")){
            return false;
        }

        if ((partner.email == undefined || partner.email == false)) {
            return false;
        }
        return true;
    },
    set_partner(partner) {
        super.set_partner(...arguments);
        if (this.is_cr_country() && this.isFactura()) {
            this.to_invoice = true;
        }
        else {
            this.to_invoice = false;
        }
    }
});

