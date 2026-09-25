from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class IndoorProvisionalProduct(models.Model):
    _name = "indoor.provisional.product"
    _description = "Producto provisional"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(string="Nombre", required=True, tracking=True)
    description = fields.Text(string="Descripción")
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    categ_id = fields.Many2one(
        "product.category",
        string="Categoría",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    product_kind = fields.Selection(
        [("goods", "Bien"), ("service", "Servicio")],
        string="Tipo de producto",
        required=True,
        default="goods",
        tracking=True,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad de medida",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit"),
        domain="[('category_id', '=', uom_category_id)]",
    )
    uom_category_id = fields.Many2one(related="uom_id.category_id")
    uom_po_id = fields.Many2one(
        "uom.uom",
        string="Unidad de compra",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit"),
        domain="[('category_id', '=', uom_category_id)]",
    )
    route_id = fields.Many2one(
        "stock.route",
        string="Ruta",
        required=True,
        default=lambda self: self._default_buy_route(),
        domain="[('product_selectable', '=', True)]",
        tracking=True,
    )
    sale_ok = fields.Boolean(string="Ventas", default=True)
    purchase_ok = fields.Boolean(string="Compras", default=True)
    cost = fields.Monetary(string="Costo", readonly=True, tracking=True)
    source = fields.Selection(
        [("manual", "Manual"), ("sale", "Venta"), ("purchase", "Compra")],
        string="Origen",
        default="manual",
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("quoted", "Cotizado"),
            ("approved", "Aprobado"),
            ("converted", "Convertido"),
            ("discarded", "Descartado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    definitive_product_id = fields.Many2one(
        "product.product",
        string="Producto definitivo",
        check_company=True,
        tracking=True,
        help="Seleccione un producto existente para vincularlo, o déjelo vacío para crear uno nuevo.",
    )
    converted_by = fields.Many2one("res.users", string="Convertido por", readonly=True)
    converted_at = fields.Datetime(string="Fecha de conversión", readonly=True)
    sale_line_ids = fields.One2many(
        "sale.order.line", "provisional_product_id", string="Líneas de venta", readonly=True
    )
    purchase_line_ids = fields.One2many(
        "purchase.order.line", "provisional_product_id", string="Líneas de compra", readonly=True
    )

    @api.model
    def _default_buy_route(self):
        return self.env.ref("purchase_stock.route_warehouse0_buy", raise_if_not_found=False)

    @api.onchange("uom_id")
    def _onchange_uom_id(self):
        if self.uom_id and (
            not self.uom_po_id or self.uom_po_id.category_id != self.uom_id.category_id
        ):
            self.uom_po_id = self.uom_id

    @api.constrains("uom_id", "uom_po_id")
    def _check_uom_category(self):
        for provisional in self:
            if provisional.uom_id.category_id != provisional.uom_po_id.category_id:
                raise ValidationError(
                    _("La unidad de venta y la unidad de compra deben pertenecer a la misma categoría.")
                )

    @api.constrains("route_id")
    def _check_buy_route(self):
        for provisional in self:
            if not provisional.route_id.rule_ids.filtered(lambda rule: rule.action == "buy"):
                raise ValidationError(_("La ruta seleccionada debe contener una regla de compra."))

    def _get_placeholder_product(self):
        self = self.with_context(active_test=False)
        template = self.env.ref("indoor_inventario.product_template_provisional_placeholder")
        return template.with_context(active_test=False).product_variant_id

    @api.model
    def _configure_placeholder_product(self):
        """Keep the single generic product selectable and clearly named."""
        template = self.env.ref(
            "indoor_inventario.product_template_provisional_placeholder",
            raise_if_not_found=False,
        )
        if template:
            template.sudo().with_context(active_test=False).write(
                {
                    "name": "Producto Provisional",
                    "default_code": False,
                    "active": True,
                    "sale_ok": True,
                    "purchase_ok": True,
                }
            )
            template.sudo().with_context(active_test=False).product_variant_ids.write(
                {"active": True, "default_code": False}
            )
        return True

    def _line_description(self):
        self.ensure_one()
        return "\n".join(filter(None, (self.name, self.description)))

    def _mark_quoted(self, source):
        for provisional in self.filtered(lambda item: item.state == "draft"):
            values = {"state": "quoted"}
            if provisional.source == "manual":
                values["source"] = source
            provisional.write(values)

    def _conversion_values(self):
        self.ensure_one()
        if not self.categ_id or not self.route_id or not self.product_kind:
            raise UserError(_("Debe definir categoría, tipo de producto y ruta antes de convertir."))
        return {
            "name": self.name,
            "description_sale": self.description,
            "description_purchase": self.description,
            "categ_id": self.categ_id.id,
            "type": "service" if self.product_kind == "service" else "consu",
            "is_storable": self.product_kind == "goods",
            "uom_id": self.uom_id.id,
            "uom_po_id": self.uom_po_id.id,
            "route_ids": [Command.set(self.route_id.ids)],
            "sale_ok": self.sale_ok,
            "purchase_ok": self.purchase_ok,
            "company_id": self.company_id.id,
        }

    def _ensure_definitive_product(self):
        self.ensure_one()
        if self.state == "discarded":
            raise UserError(_("El producto provisional %s está descartado.", self.display_name))
        product = self.definitive_product_id
        if not product:
            template = self.env["product.template"].sudo().create(self._conversion_values())
            product = template.product_variant_id
        if self.state != "converted":
            self.write(
                {
                    "definitive_product_id": product.id,
                    "state": "converted",
                    "converted_by": self.env.user.id,
                    "converted_at": fields.Datetime.now(),
                }
            )
            self.message_post(
                body=_("Convertido en el producto definitivo %s.", product.display_name)
            )
        return product

    def _set_purchase_cost(self, cost):
        self.ensure_one()
        product = self._ensure_definitive_product()
        product.sudo().with_company(self.company_id).standard_price = cost
        self.cost = cost

    def action_approve(self):
        for provisional in self:
            if provisional.state not in ("draft", "quoted"):
                raise UserError(_("Sólo se puede aprobar un producto borrador o cotizado."))
            provisional.state = "approved"
        return True

    def action_convert(self):
        for provisional in self:
            provisional._ensure_definitive_product()
        return True

    def action_discard(self):
        for provisional in self:
            if provisional.state == "converted":
                raise UserError(_("Un producto convertido no se puede descartar."))
            provisional.state = "discarded"
        return True

    def action_reset_to_draft(self):
        for provisional in self:
            if provisional.state != "discarded":
                raise UserError(_("Sólo los productos descartados pueden volver a borrador."))
            provisional.state = "draft"
        return True

    def action_open_definitive_product(self):
        self.ensure_one()
        if not self.definitive_product_id:
            raise UserError(_("Todavía no existe un producto definitivo."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "res_id": self.definitive_product_id.product_tmpl_id.id,
            "view_mode": "form",
            "target": "current",
        }
