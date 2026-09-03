/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
//import { useModel } from "@web/views/model";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
//import { _lt } from "@web/core/l10n/translation";
//import { Component, useRef } from "@odoo/owl";
import { Component, toRaw, useRef } from "@odoo/owl";


export class AffiliateController extends Component {
    setup() {
        this.actionService = useService("action");
        this.model = useModelWithSampleData(this.props.Model, toRaw(this.props.modelParams));

        useSetupView({
            rootRef: useRef("root"),
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
            getContext: () => this.getContext(),
        });

    }

    async onFilterEconomicActivity(value){
//        console.log(this);
//        var $target = $(e.target);
//        var value = $target.val();
//        console.log(value);
        await this._onFilterEconomicActivity(value);
    }
    async _onFilterEconomicActivity(value){
        console.log(this)
        if (value != ""){
            this.model.searchParams.measure = value
        }
        else {
            this.model.searchParams.measure = ""
        }
//        this.model.searchParams.measure = value
        this.model.searchParams.domain = this.env.searchModel._domain

        await this.model.load(this.model.searchParams)
        this.render()
    }

    /**
     * @param {Object} row
     */
    onRowClicked(row, measure) {
//        console.log(row)
//        console.log(this)

//        if (row.value === undefined) {
//            return;
//        }
//        let activity = document.getElementsByName("filter_economic_activity")[0].value
        const context = Object.assign({}, this.model.searchParams.context);

//        console.log(activity)

        var domain_tr = [['detailed_type_product', '=', row]];

//        console.log(measure)
        if (measure != ""){
            domain_tr = domain_tr.concat([['economic_activity_id', '=', parseInt(measure)]]);
        }

        let domain = this.model.searchParams.domains[0].arrayRepr;

        domain_tr = domain_tr.concat(domain);
        console.log(domain_tr)

        this.actionService.doAction({
            type: "ir.actions.act_window",
//            name: _lt('Activities'),
//            name: 'Affiliate',
            name: this.model.metaData.title,
            res_model: this.props.resModel,
            views: [[false, 'list'], [false, 'form']],
            view_mode: "list",
            target: "current",
            context: context,
            domain: domain_tr,
        });
    }
}

AffiliateController.template = "l10n_cr_reports.AffiliateView";
AffiliateController.components = { Layout, SearchBar};
AffiliateController.props = {
    ...standardViewProps,
    Model: Function,
    modelParams: Object,
    Renderer: Function,
};
