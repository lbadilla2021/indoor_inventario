/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

const PROTECTED_MODELS = new Set([
    "product.template",
    "product.product",
    "stock.picking",
]);

patch(FormController.prototype, {
    get modelParams() {
        const params = super.modelParams;
        if (params.config.resId && PROTECTED_MODELS.has(params.config.resModel)) {
            params.config.mode = "readonly";
        }
        return params;
    },

    get isIndoorProtectedForm() {
        return PROTECTED_MODELS.has(this.props.resModel);
    },

    get isIndoorProtectedReadonlyForm() {
        return (
            this.isIndoorProtectedForm &&
            this.canEdit &&
            Boolean(this.model?.root?.resId) &&
            !this.model.root.isInEdition
        );
    },

    async enterIndoorEditMode() {
        await this.model.root.switchMode("edit");
    },

    async onRecordSaved(record, changes) {
        const result = await super.onRecordSaved(record, changes);
        if (
            this.isIndoorProtectedForm &&
            record.resId &&
            record.isInEdition
        ) {
            record._switchMode("readonly");
        }
        return result;
    },

    async discard() {
        const protectedExistingRecord =
            this.isIndoorProtectedForm && Boolean(this.model.root.resId);
        const result = await super.discard(...arguments);
        if (
            protectedExistingRecord &&
            !this.env.inDialog &&
            this.model.root.isInEdition
        ) {
            await this.model.root.switchMode("readonly");
        }
        return result;
    },

    async create() {
        const result = await super.create(...arguments);
        if (
            this.isIndoorProtectedForm &&
            this.model.root.isNew &&
            !this.model.root.isInEdition
        ) {
            await this.model.root.switchMode("edit");
        }
        return result;
    },

    async onPagerUpdate(params) {
        const result = await super.onPagerUpdate(params);
        if (
            this.isIndoorProtectedForm &&
            this.model.root.resId &&
            this.model.root.isInEdition
        ) {
            await this.model.root.switchMode("readonly");
        }
        return result;
    },
});
