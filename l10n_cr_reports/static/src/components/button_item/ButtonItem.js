/** @odoo-module **/
import { Component } from "@odoo/owl";


export class ButtonItem extends Component {
    setup() {
//        this.model = this.props.model;
        console.log(this);
    }
}
ButtonItem.template = "api_expiration_server.ButtonItem";


//odoo.define("api_expiration_server.ButtonItem", function (require) {
//    "use strict";
//    const { Component } = owl;
//    const { useState } = owl.hooks;
//
//    class ButtonItem extends Component {
//      /**
//       * @override
//       */
//      constructor(...args) {
//        super(...args);
//      }
//
//    }
//
//    ButtonItem.template = 'api_expiration_server.ButtonItem';
//    return ButtonItem
//
//});
