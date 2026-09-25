from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

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
            line.product_uom = provisional.uom_po_id
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
                values.setdefault("product_uom", provisional.uom_po_id.id)
                values.setdefault("name", provisional._line_description())
        lines = super().create(vals_list)
        lines.mapped("provisional_product_id")._mark_quoted("purchase")
        return lines

    def _provisional_cost_company_currency(self):
        self.ensure_one()
        price = self.price_unit * (1.0 - (getattr(self, "discount", 0.0) or 0.0) / 100.0)
        conversion_date = fields.Date.to_date(self.order_id.date_order) or fields.Date.context_today(self)
        price = self.order_id.currency_id._convert(
            price,
            self.company_id.currency_id,
            self.company_id,
            conversion_date,
            round=False,
        )
        return self.product_uom._compute_price(price, self.provisional_product_id.uom_id)

    def _replace_provisional_product(self, product):
        self.ensure_one()
        self.with_context(indoor_provisional_conversion=True).write(
            {
                "product_id": product.id,
                "product_uom": product.uom_po_id.id,
                "name": self.name,
                "price_unit": self.price_unit,
            }
        )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _convert_provisional_lines(self):
        cost_data = defaultdict(lambda: [0.0, 0.0])
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
                provisional = line.provisional_product_id
                cost = line._provisional_cost_company_currency()
                quantity = line.product_uom._compute_quantity(
                    line.product_qty, provisional.uom_id
                )
                weight = quantity if quantity > 0 else 1.0
                cost_data[provisional][0] += cost * weight
                cost_data[provisional][1] += weight
                product = provisional._ensure_definitive_product()
                line._replace_provisional_product(product)
        return cost_data

    def _apply_provisional_costs(self, cost_data):
        for provisional, (total, quantity) in cost_data.items():
            provisional._set_purchase_cost(total / quantity)

    def button_confirm(self):
        cost_data = self._convert_provisional_lines()
        result = super().button_confirm()
        confirmed = self.filtered(lambda order: order.state in ("purchase", "done"))
        if confirmed:
            confirmed._apply_provisional_costs(cost_data)
        return result

    def button_approve(self, force=False):
        cost_data = self._convert_provisional_lines()
        result = super().button_approve(force=force)
        self._apply_provisional_costs(cost_data)
        return result
