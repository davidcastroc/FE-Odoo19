/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
//import { ButtonItem } from "../components/button_item/ButtonItem";
import { formatPercentage, formatFloat } from "@web/views/fields/formatters";


export class AffiliateRenderer extends Component {
    setup() {
        this.model = this.props.model;
        this.filter = useState({ value: "" });
//        const ref = useRef('input');
    }
    formatFloat(value) {
        return '₡ ' + formatFloat(value, { digits: [false, 1] });
    }
    onMouseEnter(ev) {
        ev.currentTarget.classList.add("o_cell_hover");
    }
    onMouseLeave() {
//        this.el
//            .querySelectorAll(".o_cell_hover")
//            .forEach((elt) => elt.classList.remove("o_cell_hover"));
    }

}
AffiliateRenderer.template = "l10n_cr_reports.AffiliateRenderer";
//AffiliateRenderer.components = {ButtonItem};
AffiliateRenderer.props = ["model", "onRowClicked", "onFilterEconomicActivity"];
