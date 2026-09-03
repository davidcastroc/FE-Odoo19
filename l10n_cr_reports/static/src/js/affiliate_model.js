/** @odoo-module **/
//import { _lt } from "@web/core/l10n/translation";
import { Model } from "@web/model/model";
import { KeepLast } from "@web/core/utils/concurrency";


export class AffiliateModel extends Model {
    setup() {
        this.keepLast = new KeepLast();
//        this.interval = 'general';
//        this.measure = 'percent';
//        this.dom = [];
        const _load = this._load.bind(this);
        this.metaData = {};
        this.data = null;
        this.searchParams = null;
    }

    /**
     * @param {SearchParams} searchParams
     */
//    load(searchParams) {
//        const { context, domain } = searchParams;
//        this.searchParams = { context };
//        this.searchParams.domains = [{ arrayRepr: domain, description: null }];
//
//        return this._load(this.metaData);
//
//    }

    /**
     * @param {SearchParams} searchParams
     */
    load(searchParams) {
//        console.log(searchParams)
        const { context, domain } = searchParams;
        this.searchParams = { context };
        this.searchParams.domains = [{ arrayRepr: domain, description: null }];
//        if (comparison) {
//            this.searchParams.domains = comparison.domains;
//        } else {
//            this.searchParams.domains = [{ arrayRepr: domain, description: null }];
//        }
//        const { cohort_interval, cohort_measure } = searchParams.context;
//        this.metaData.interval = cohort_interval || this.metaData.interval;
//
//        this.metaData.measure = processMeasure(cohort_measure) || this.metaData.measure;
//        this.metaData.measures = computeReportMeasures(
//            this.metaData.fields,
//            this.metaData.fieldAttrs,
//            [this.metaData.measure]
//        );
        if (searchParams.measure != ""){
            this.metaData.measure = searchParams.measure
        }
        else {
            this.metaData.measure = ""
        }
        return this._load(this.metaData);
    }


    /**
     * @protected
     * @param {Object} metaData
     */
    async _load(metaData) {
        this.data = await this.keepLast.add(this._fetchData(metaData));
    }
    /**
     * @protected
     * @param {Object} metaData
     */
    async _fetchData(metaData) {
        var self = this;
//        console.log(this);
        return Promise.all(
            this.searchParams.domains.map(({ arrayRepr: domain }) => {
                var complete_domain = domain;
//                complete_domain = complete_domain.concat(this.dom);
                return this.orm.call(self.env.searchModel.resModel, "get_activity_data", [], {
                    domain: complete_domain,
                    context: this.searchParams.context,
                    measure: metaData.measure,
                });
            })
        );
    }
}
