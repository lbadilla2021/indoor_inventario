/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useEffect } from "@odoo/owl";

const AUTO_COMMIT_DELAY = 450;

export class IndoorBarcodeAutoTabField extends CharField {
    setup() {
        super.setup();
        this.autoCommitTimer = null;

        useEffect(
            (inputEl) => {
                if (!inputEl || this.props.readonly) {
                    return;
                }

                const onInput = () => this.scheduleCommitAndFocus();
                const onKeydown = (ev) => {
                    if (ev.key === "Enter" || ev.key === "Tab") {
                        ev.preventDefault();
                        this.commitAndFocusNext();
                    }
                };

                inputEl.addEventListener("input", onInput);
                inputEl.addEventListener("keydown", onKeydown);
                return () => {
                    window.clearTimeout(this.autoCommitTimer);
                    inputEl.removeEventListener("input", onInput);
                    inputEl.removeEventListener("keydown", onKeydown);
                };
            },
            () => [this.input.el, this.props.readonly]
        );
    }

    scheduleCommitAndFocus() {
        window.clearTimeout(this.autoCommitTimer);
        this.autoCommitTimer = window.setTimeout(
            () => this.commitAndFocusNext(),
            AUTO_COMMIT_DELAY
        );
    }

    async commitAndFocusNext() {
        window.clearTimeout(this.autoCommitTimer);
        const inputEl = this.input.el;
        const barcode = this.parse(inputEl?.value || "");
        if (!inputEl || !barcode) {
            return;
        }
        if (barcode !== (this.props.record.data[this.props.name] || "")) {
            await this.props.record.update({ [this.props.name]: barcode });
        }
        this.focusQuantityField();
    }

    focusQuantityField() {
        const rowEl = this.input.el.closest("tr");
        const containerEl = rowEl || this.input.el.closest(".o_form_view");
        const quantityEl = containerEl?.querySelector(
            ".o_field_widget[name='quantity'] input, .o_field_widget[name='quantity'] input[type='text']"
        );
        if (quantityEl instanceof HTMLElement) {
            quantityEl.focus();
            quantityEl.select?.();
        }
    }
}

export const indoorBarcodeAutoTabField = {
    ...charField,
    component: IndoorBarcodeAutoTabField,
};

registry.category("fields").add("indoor_barcode_auto_tab", indoorBarcodeAutoTabField);
