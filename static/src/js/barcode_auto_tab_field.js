/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { BarcodeDialog } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";

const AUTO_COMMIT_DELAY = 450;

export class IndoorCameraQuantityDialog extends Component {
    static template = "indoor_inventario.IndoorCameraQuantityDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        barcode: String,
        product: Object,
        onSave: Function,
        onCancel: Function,
    };

    setup() {
        this.quantityInput = useRef("quantity");
        this.state = useState({
            quantity: 1,
            lotName: "",
            note: "",
            saving: false,
            error: "",
        });
        onMounted(() => {
            this.quantityInput.el?.focus();
            this.quantityInput.el?.select();
        });
    }

    async save() {
        const quantity = Number(this.state.quantity);
        if (!Number.isFinite(quantity) || quantity <= 0) {
            this.state.error = _t("La cantidad debe ser mayor que cero.");
            return;
        }
        const lotName = this.state.lotName.trim();
        if (this.props.product.tracking !== "none" && !lotName) {
            this.state.error = _t("Debe indicar un lote o número de serie.");
            return;
        }
        this.state.saving = true;
        this.state.error = "";
        try {
            if (await this.props.onSave(quantity, lotName, this.state.note.trim())) {
                this.props.close();
            }
        } finally {
            this.state.saving = false;
        }
    }

    cancel() {
        this.props.onCancel();
        this.props.close();
    }

    onQuantityKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.save();
        }
    }
}

export class IndoorBarcodeAutoTabField extends CharField {
    static template = "indoor_inventario.IndoorBarcodeAutoTabField";
    static props = {
        ...CharField.props,
        camera: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.addDialog = useOwnedDialogs();
        this.autoCommitTimer = null;
        this.cameraModeActive = false;

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

    getMany2OneId(fieldName) {
        return this.props.record.data[fieldName]?.[0] || false;
    }

    scanWithCamera() {
        return new Promise((resolve) => {
            let settled = false;
            const finish = (barcode) => {
                if (!settled) {
                    settled = true;
                    resolve(barcode || false);
                }
            };
            this.addDialog(
                BarcodeDialog,
                {
                    facingMode: "environment",
                    onResult: (barcode) => finish(this.parse(barcode || "")),
                    onError: () => finish(false),
                },
                {
                    // BarcodeDialog closes before invoking onResult. Defer the
                    // cancellation result so a successful scan wins the race.
                    onClose: () => window.setTimeout(() => finish(false), 0),
                }
            );
        });
    }

    async findProduct(barcode) {
        return this.orm.searchRead(
            "product.product",
            [["barcode", "=", barcode]],
            ["display_name", "uom_id", "tracking"],
            { limit: 2 }
        );
    }

    async findLot(productId, lotName) {
        return this.orm.searchRead(
            "stock.lot",
            [
                ["product_id", "=", productId],
                ["name", "=", lotName],
            ],
            ["display_name"],
            { limit: 2 }
        );
    }

    confirmAndCreateLine(product, barcode, sessionId, locationId) {
        return new Promise((resolve) => {
            let settled = false;
            const finish = (continueScanning) => {
                if (!settled) {
                    settled = true;
                    resolve(continueScanning);
                }
            };
            this.addDialog(
                IndoorCameraQuantityDialog,
                {
                    barcode,
                    product,
                    onSave: async (quantity, lotName, note) => {
                        try {
                            let lotId = false;
                            if (product.tracking !== "none") {
                                const lots = await this.findLot(product.id, lotName);
                                if (lots.length !== 1) {
                                    const message = lots.length
                                        ? _t(
                                              "Existe más de un lote o serie llamado %s para este producto.",
                                              lotName
                                          )
                                        : _t(
                                              "No existe el lote o serie %s para este producto.",
                                              lotName
                                          );
                                    this.notification.add(message, { type: "warning" });
                                    return false;
                                }
                                lotId = lots[0].id;
                            }
                            const values = {
                                session_id: sessionId,
                                location_id: locationId,
                                barcode,
                                product_id: product.id,
                                quantity,
                            };
                            if (lotId) {
                                values.lot_id = lotId;
                            }
                            if (note) {
                                values.note = note;
                            }
                            await this.orm.create("indoor.inventory.count.line", [
                                values,
                            ]);
                            this.notification.add(
                                _t("Lectura registrada: %s", product.display_name),
                                { type: "success" }
                            );
                            finish(true);
                            return true;
                        } catch (error) {
                            const message =
                                error?.data?.message ||
                                error?.message ||
                                _t("No fue posible registrar la lectura.");
                            this.notification.add(message, { type: "danger" });
                            return false;
                        }
                    },
                    onCancel: () => finish(false),
                },
                { onClose: () => finish(false) }
            );
        });
    }

    async onCameraScan() {
        if (this.cameraModeActive) {
            return;
        }
        const sessionId = this.getMany2OneId("session_id");
        const locationId = this.getMany2OneId("location_id");
        if (!sessionId || !locationId) {
            this.notification.add(
                _t("Seleccione una sesión y una ubicación antes de iniciar la cámara."),
                { type: "warning" }
            );
            return;
        }
        if (!["draft", "in_progress"].includes(this.props.record.data.state)) {
            this.notification.add(_t("La sesión debe estar abierta para registrar lecturas."), {
                type: "warning",
            });
            return;
        }

        this.cameraModeActive = true;
        window.clearTimeout(this.autoCommitTimer);
        try {
            while (this.cameraModeActive) {
                const barcode = await this.scanWithCamera();
                if (!barcode) {
                    break;
                }
                if ("vibrate" in browser.navigator) {
                    browser.navigator.vibrate(100);
                }

                const products = await this.findProduct(barcode);
                if (products.length !== 1) {
                    const message = products.length
                        ? _t("Existe más de un producto con el código %s.", barcode)
                        : _t("No se encontró un producto con el código %s.", barcode);
                    this.notification.add(message, { type: "warning" });
                    continue;
                }
                const product = products[0];
                const continueScanning = await this.confirmAndCreateLine(
                    product,
                    barcode,
                    sessionId,
                    locationId
                );
                if (!continueScanning) {
                    break;
                }
            }
        } finally {
            this.cameraModeActive = false;
        }
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
