from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    provisional_product_id = fields.Many2one(
        "indoor.provisional.product",
        string="Producto provisional",
        check_company=True,
        domain="[('state', 'not in', ('discarded', 'converted')), ('company_id', '=', company_id)]",
        copy=True,
    )
    is_provisional_placeholder = fields.Boolean(
        compute="_compute_is_provisional_placeholder"
    )

    @api.depends("product_id")
    def _compute_is_provisional_placeholder(self):
        placeholder = self.env["indoor.provisional.product"]._get_placeholder_product()
        for line in self:
            line.is_provisional_placeholder = line.product_id == placeholder

    @api.onchange("product_id")
    def _onchange_product_id_provisional(self):
        placeholder = self.env["indoor.provisional.product"]._get_placeholder_product()
        for line in self:
            if (
                line.provisional_product_id
                and line.product_id != placeholder
                and line.product_id != line.provisional_product_id.definitive_product_id
            ):
                line.provisional_product_id = False

    @api.onchange("provisional_product_id")
    def _onchange_provisional_product_id(self):
        for line in self:
            provisional = line.provisional_product_id
            if not provisional:
                continue
            if provisional.company_id != line.order_id.company_id:
                raise ValidationError(_("El producto provisional pertenece a otra compañía."))
            product = (
                provisional.definitive_product_id
                if provisional.state == "converted"
                else provisional._get_placeholder_product()
            )
            line.product_id = product
            line.product_template_id = product.product_tmpl_id
            line.product_uom = provisional.uom_id
            line.name = provisional._line_description()

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            provisional = self.env["indoor.provisional.product"].browse(
                values.get("provisional_product_id")
            )
            if provisional:
                product = provisional.definitive_product_id or provisional._get_placeholder_product()
                values.setdefault("product_id", product.id)
                values.setdefault("product_uom", provisional.uom_id.id)
                values.setdefault("name", provisional._line_description())
        lines = super().create(vals_list)
        lines.mapped("provisional_product_id")._mark_quoted("sale")
        return lines

    def _replace_provisional_product(self, product):
        self.ensure_one()
        self.with_context(indoor_provisional_conversion=True).write(
            {
                "product_id": product.id,
                "product_uom": product.uom_id.id,
                "name": self.name,
                "price_unit": self.price_unit,
            }
        )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        for order in self:
            placeholder = self.env["indoor.provisional.product"]._get_placeholder_product()
            incomplete = order.order_line.filtered(
                lambda item: not item.display_type
                and item.product_id == placeholder
                and not item.provisional_product_id
            )
            if incomplete:
                raise UserError(
                    _("Debe seleccionar el producto provisional en todas las líneas marcadas como Producto Provisional.")
                )
            for line in order.order_line.filtered(
                lambda item: not item.display_type and item.provisional_product_id
            ):
                product = line.provisional_product_id._ensure_definitive_product()
                line._replace_provisional_product(product)
        return super().action_confirm()
