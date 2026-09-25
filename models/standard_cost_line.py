from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class IndoorStandardCostLine(models.Model):
    _name = "indoor.standard.cost.line"
    _description = "Línea de actualización de costo estándar"
    _order = "batch_id desc, product_id"

    batch_id = fields.Many2one(
        "indoor.standard.cost.batch", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True, index=True)
    closing_date = fields.Date(related="batch_id.closing_date", store=True, index=True)
    product_id = fields.Many2one("product.product", required=True, index=True)
    product_category_id = fields.Many2one(related="product_id.categ_id", store=True)
    uom_id = fields.Many2one("uom.uom", required=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)

    stock_qty = fields.Float(digits="Product Unit of Measure", readonly=True)
    old_standard_price = fields.Float(digits="Product Price", readonly=True)
    stock_value_before = fields.Monetary(readonly=True)
    total_purchase_qty = fields.Float(digits="Product Unit of Measure", readonly=True)
    total_purchase_value = fields.Monetary(readonly=True)
    purchase_count = fields.Integer(readonly=True)
    calculated_standard_price = fields.Float(digits="Product Price", readonly=True)
    approved_standard_price = fields.Float(
        digits="Product Price",
    )
    approved_changed_by = fields.Many2one("res.users", readonly=True)
    approved_changed_at = fields.Datetime(readonly=True)
    absolute_difference = fields.Float(
        compute="_compute_variations", store=True, digits="Product Price"
    )
    percentage_difference = fields.Float(compute="_compute_variations", store=True)
    stock_value_after = fields.Monetary(compute="_compute_variations", store=True)
    revaluation_difference = fields.Monetary(compute="_compute_variations", store=True)
    warning = fields.Text(readonly=True)
    validation_status = fields.Selection(
        [
            ("ready", "Listo"),
            ("no_purchase", "Sin compras"),
            ("stale", "Compra obsoleta"),
            ("invalid_method", "Método inválido"),
            ("negative_stock", "Stock negativo"),
        ],
        required=True,
        default="ready",
        readonly=True,
        index=True,
    )
    warning_level = fields.Selection(
        [("normal", "Normal"), ("warning", "Advertencia"), ("critical", "Crítico")],
        compute="_compute_variations", store=True,
    )

    purchase_1_id = fields.Many2one("purchase.order", readonly=True)
    purchase_1_line_id = fields.Many2one("purchase.order.line", readonly=True)
    purchase_1_partner_id = fields.Many2one("res.partner", readonly=True)
    purchase_1_date = fields.Datetime(readonly=True)
    purchase_1_qty = fields.Float(digits="Product Unit of Measure", readonly=True)
    purchase_1_price = fields.Float(digits="Product Price", readonly=True)
    purchase_1_receipt_ids = fields.Many2many(
        "stock.picking", "indoor_cost_line_pick_1_rel", "line_id", "picking_id", readonly=True
    )
    purchase_2_id = fields.Many2one("purchase.order", readonly=True)
    purchase_2_line_id = fields.Many2one("purchase.order.line", readonly=True)
    purchase_2_partner_id = fields.Many2one("res.partner", readonly=True)
    purchase_2_date = fields.Datetime(readonly=True)
    purchase_2_qty = fields.Float(digits="Product Unit of Measure", readonly=True)
    purchase_2_price = fields.Float(digits="Product Price", readonly=True)
    purchase_2_receipt_ids = fields.Many2many(
        "stock.picking", "indoor_cost_line_pick_2_rel", "line_id", "picking_id", readonly=True
    )
    purchase_3_id = fields.Many2one("purchase.order", readonly=True)
    purchase_3_line_id = fields.Many2one("purchase.order.line", readonly=True)
    purchase_3_partner_id = fields.Many2one("res.partner", readonly=True)
    purchase_3_date = fields.Datetime(readonly=True)
    purchase_3_qty = fields.Float(digits="Product Unit of Measure", readonly=True)
    purchase_3_price = fields.Float(digits="Product Price", readonly=True)
    purchase_3_receipt_ids = fields.Many2many(
        "stock.picking", "indoor_cost_line_pick_3_rel", "line_id", "picking_id", readonly=True
    )

    _sql_constraints = [
        (
            "unique_product_batch",
            "UNIQUE(batch_id, product_id)",
            "Un producto solo puede aparecer una vez en el mismo cierre.",
        )
    ]

    @api.depends("approved_standard_price", "old_standard_price", "stock_qty", "batch_id.warning_threshold", "batch_id.critical_threshold")
    def _compute_variations(self):
        for line in self:
            difference = line.approved_standard_price - line.old_standard_price
            line.absolute_difference = difference
            line.percentage_difference = (
                difference / line.old_standard_price * 100.0
                if line.old_standard_price else (100.0 if difference else 0.0)
            )
            line.stock_value_after = line.stock_qty * line.approved_standard_price
            line.revaluation_difference = line.stock_value_after - line.stock_value_before
            percentage = abs(line.percentage_difference)
            if percentage > line.batch_id.critical_threshold:
                line.warning_level = "critical"
            elif percentage > line.batch_id.warning_threshold:
                line.warning_level = "warning"
            else:
                line.warning_level = "normal"

    @api.constrains("approved_standard_price")
    def _check_approved_price(self):
        for line in self:
            if float_compare(line.approved_standard_price, 0.0, precision_digits=12) < 0:
                raise ValidationError(_("El costo aprobado no puede ser negativo."))

    def write(self, vals):
        if any(line.batch_id.state in ("approved", "applied", "cancelled") for line in self):
            raise UserError(_("No se pueden editar líneas de un cierre aprobado, aplicado o cancelado."))
        if "approved_standard_price" in vals:
            vals = dict(vals, approved_changed_by=self.env.user.id, approved_changed_at=fields.Datetime.now())
        return super().write(vals)

    def unlink(self):
        if any(line.batch_id.state in ("approved", "applied") for line in self):
            raise UserError(_("No se pueden eliminar líneas aprobadas o aplicadas."))
        return super().unlink()
