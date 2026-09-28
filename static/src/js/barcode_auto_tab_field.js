/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import * as BarcodeScanner from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useEffect } from "@odoo/owl";

const AUTO_COMMIT_DELAY = 450;

export class IndoorBarcodeAutoTabField extends CharField {
    static template = "indoor_inventario.IndoorBarcodeAutoTabField";
    static props = {
        ...CharField.props,
        camera: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
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

    get hasCameraButton() {
        return (
            this.props.camera &&
            !this.props.readonly &&
            isBarcodeScannerSupported()
        );
    }

    async onCameraScan() {
        let barcode;
        try {
            barcode = await BarcodeScanner.scanBarcode(this.env);
        } catch {
            return;
        }
        barcode = this.parse(barcode || "");
        if (!barcode) {
            this.notification.add(_t("No se detectó ningún código. Inténtelo nuevamente."), {
                type: "warning",
            });
            return;
        }

        window.clearTimeout(this.autoCommitTimer);
        await this.props.record.update({ [this.props.name]: barcode });
        if ("vibrate" in browser.navigator) {
            browser.navigator.vibrate(100);
        }
        this.focusQuantityField();
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
    supportedOptions: [
        ...charField.supportedOptions,
        {
            label: _t("Escanear con cámara"),
            name: "camera",
            type: "boolean",
        },
    ],
    extractProps: (args) => ({
        ...charField.extractProps(args),
        camera: Boolean(args.options.camera),
    }),
};

registry.category("fields").add("indoor_barcode_auto_tab", indoorBarcodeAutoTabField);
