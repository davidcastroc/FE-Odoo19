/** @odoo-module **/
import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { _lt } from "@web/core/l10n/translation";

import { AffiliateController } from "./affiliate_controller";
import { AffiliateModel }  from "./affiliate_model";
import { AffiliateRenderer } from "./affiliate_renderer";


export const AffiliateView = {
    type: "affiliate",
    display_name: "Affiliate Analysis",
    icon: "fa-indent",
    multiRecord: true,
    searchMenuTypes: ["filter", "favorite"],
    Model: AffiliateModel,
    Controller: AffiliateController,
    Renderer: AffiliateRenderer,

    props: (genericProps, view) => {
        let modelParams;
        if (genericProps.state) {
            modelParams = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel } = genericProps;
            modelParams = {
                fields: fields,
                resModel: resModel,
            };
        }

        return {
            ...genericProps,
            modelParams,
            Model: view.Model,
            Renderer: view.Renderer,
        };
    },
};

registry.category("views").add("affiliate", AffiliateView);
