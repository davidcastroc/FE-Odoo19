import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
    },
    async validateOrder(isForceValidate) {
        let order = this.currentOrder;
        const existingNonDocumentPayment = order.payment_ids.find(
            (payment) => payment.payment_method_id.non_document
        );

        if (existingNonDocumentPayment){
            order.non_document = true
        }
        return await super.validateOrder(...arguments);
    },
});
