from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    CUSTOM_USABLE_WIDTH = 190.0
    CUSTOM_USABLE_HEIGHT = 250.0
    CUSTOM_LABEL_GAP = 5.0

    print_format = fields.Selection(
        selection_add=[("custom", "Personalizado")],
        ondelete={"custom": "set default"},
    )
    custom_label_width = fields.Float(
        string="Ancho (mm)", default=50.0, digits=(6, 2)
    )
    custom_label_height = fields.Float(
        string="Alto (mm)", default=30.0, digits=(6, 2)
    )

    @api.depends("print_format", "custom_label_width", "custom_label_height")
    def _compute_dimensions(self):
        super()._compute_dimensions()
        for wizard in self.filtered(lambda record: record.print_format == "custom"):
            wizard.columns = (
                int(
                    (self.CUSTOM_USABLE_WIDTH + self.CUSTOM_LABEL_GAP)
                    // (wizard.custom_label_width + self.CUSTOM_LABEL_GAP)
                )
                if wizard.custom_label_width > 0
                else 0
            )
            wizard.rows = (
                int(
                    (self.CUSTOM_USABLE_HEIGHT + self.CUSTOM_LABEL_GAP)
                    // (wizard.custom_label_height + self.CUSTOM_LABEL_GAP)
                )
                if wizard.custom_label_height > 0
                else 0
            )

    @api.constrains("print_format", "custom_label_width", "custom_label_height")
    def _check_custom_label_dimensions(self):
        for wizard in self.filtered(lambda record: record.print_format == "custom"):
            if wizard.custom_label_width <= 0 or wizard.custom_label_height <= 0:
                raise ValidationError(
                    _("El ancho y el alto de la etiqueta deben ser mayores que cero.")
                )
            if wizard.custom_label_width > self.CUSTOM_USABLE_WIDTH:
                raise ValidationError(
                    _("El ancho no puede superar los 190 mm del área útil.")
                )
            if wizard.custom_label_height > self.CUSTOM_USABLE_HEIGHT:
                raise ValidationError(
                    _("El alto no puede superar los 250 mm del área útil.")
                )

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        if self.print_format == "custom":
            xml_id = "indoor_inventario.action_report_product_label_custom"
            data.update(
                custom_label_width=self.custom_label_width,
                custom_label_height=self.custom_label_height,
                custom_label_rows=self.rows,
                custom_label_columns=self.columns,
            )
        return xml_id, data
