from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_open_purchase_order_modal(self):
        self.ensure_one()
        purchase = self.purchase_id
        if not purchase and self.origin:
            purchase = self.env["purchase.order"].search(
                [
                    ("name", "=", self.origin),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if not purchase:
            raise UserError(_("No se encontró una orden de compra asociada a este documento origen."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Orden de compra"),
            "res_model": "purchase.order",
            "res_id": purchase.id,
            "view_mode": "form",
            "views": [(self.env.ref("purchase.purchase_order_form").id, "form")],
            "target": "new",
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
                "form_view_initial_mode": "view",
            },
        }


class StockMove(models.Model):
    _inherit = "stock.move"

    purchase_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de compra",
        related="purchase_line_id.currency_id",
        readonly=True,
    )
    purchase_price_unit = fields.Float(
        string="Precio compra",
        related="purchase_line_id.price_unit",
        digits="Product Price",
        readonly=True,
    )
    vendor_invoice_ref = fields.Char(
        string="Factura",
        copy=False,
        help="Número de la factura del proveedor correspondiente a esta línea recibida.",
    )
