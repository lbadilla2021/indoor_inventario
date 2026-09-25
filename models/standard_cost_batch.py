from collections import defaultdict
from datetime import datetime, time
from io import BytesIO

from odoo import Command, api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import xlsxwriter
from odoo.tools.float_utils import float_compare, float_is_zero


class IndoorStandardCostBatch(models.Model):
    _name = "indoor.standard.cost.batch"
    _description = "Actualización mensual de costos estándar"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "closing_date desc, id desc"

    name = fields.Char(default="Nuevo", required=True, copy=False, readonly=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, tracking=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    closing_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    calculation_date = fields.Datetime(readonly=True)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("calculated", "Calculado"),
            ("approved", "Aprobado"),
            ("applied", "Aplicado"),
            ("cancelled", "Cancelado"),
        ],
        default="draft", required=True, readonly=True, index=True, tracking=True,
    )
    calculated_by = fields.Many2one("res.users", readonly=True)
    calculated_at = fields.Datetime(readonly=True)
    approved_by = fields.Many2one("res.users", readonly=True)
    approved_at = fields.Datetime(readonly=True)
    applied_by = fields.Many2one("res.users", readonly=True)
    applied_at = fields.Datetime(readonly=True)
    line_ids = fields.One2many("indoor.standard.cost.line", "batch_id", copy=False)
    notes = fields.Html()
    purchase_limit = fields.Integer(readonly=True, default=3)
    stale_days = fields.Integer(readonly=True, default=180)
    warning_threshold = fields.Float(readonly=True, default=10.0)
    critical_threshold = fields.Float(readonly=True, default=20.0)
    product_count = fields.Integer(compute="_compute_totals", store=True)
    total_value_before = fields.Monetary(compute="_compute_totals", store=True)
    total_value_after = fields.Monetary(compute="_compute_totals", store=True)
    total_revaluation = fields.Monetary(compute="_compute_totals", store=True)
    applied_closing_key = fields.Char(compute="_compute_applied_closing_key", store=True)

    _sql_constraints = [
        (
            "unique_applied_closing",
            "UNIQUE(company_id, applied_closing_key)",
            "Ya existe un cierre aplicado para esta compañía y fecha.",
        )
    ]

    @api.depends("state", "closing_date")
    def _compute_applied_closing_key(self):
        for batch in self:
            batch.applied_closing_key = (
                fields.Date.to_string(batch.closing_date)
                if batch.state == "applied" and batch.closing_date else False
            )

    @api.depends("line_ids.stock_value_before", "line_ids.stock_value_after", "line_ids.revaluation_difference")
    def _compute_totals(self):
        for batch in self:
            batch.product_count = len(batch.line_ids)
            batch.total_value_before = sum(batch.line_ids.mapped("stock_value_before"))
            batch.total_value_after = sum(batch.line_ids.mapped("stock_value_after"))
            batch.total_revaluation = sum(batch.line_ids.mapped("revaluation_difference"))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = sequence.next_by_code("indoor.standard.cost.batch") or "Nuevo"
        return super().create(vals_list)

    def write(self, vals):
        if any(batch.state == "applied" for batch in self) and set(vals) - {"message_follower_ids", "activity_ids"}:
            raise UserError(_("Un cierre aplicado es inmutable."))
        return super().write(vals)

    def unlink(self):
        if any(batch.state in ("approved", "applied") for batch in self):
            raise UserError(_("No se puede eliminar un cierre aprobado o aplicado."))
        return super().unlink()

    @api.constrains("closing_date")
    def _check_closing_date(self):
        for batch in self:
            if batch.closing_date and batch.closing_date > fields.Date.context_today(batch):
                raise ValidationError(_("La fecha de cierre no puede estar en el futuro."))

    def _get_setting_int(self, key, default, minimum=0, maximum=None):
        value = self.env["ir.config_parameter"].sudo().get_param(key, str(default))
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default
        value = max(minimum, value)
        return min(maximum, value) if maximum is not None else value

    def _get_setting_float(self, key, default):
        value = self.env["ir.config_parameter"].sudo().get_param(key, str(default))
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return default

    def _receipt_sign(self, move):
        """Mirror the relevant Odoo 18 purchase received-quantity semantics."""
        if move._is_purchase_return():
            return -1 if (not move.origin_returned_move_id or move.to_refund) else 0
        if not move._should_count_for_quantity_received():
            return 0
        return 1

    def _prepare_purchase_candidates(self, products, cutoff):
        moves = self.env["stock.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("product_id", "in", products.ids),
                ("purchase_line_id", "!=", False),
                ("purchase_line_id.order_id.state", "in", ("purchase", "done")),
                ("state", "=", "done"),
                ("date", "<=", cutoff),
            ],
            order="date desc, id desc",
        )
        aggregates = {}
        for move in moves:
            sign = self._receipt_sign(move)
            if not sign:
                continue
            line = move.purchase_line_id
            item = aggregates.setdefault(
                line.id,
                {"line": line, "qty": 0.0, "date": False, "picking_ids": set()},
            )
            qty = move.product_uom._compute_quantity(
                move.quantity, move.product_id.uom_id, rounding_method="HALF-UP"
            )
            item["qty"] += sign * qty
            if sign > 0:
                item["date"] = max(filter(None, (item["date"], move.date)))
            if move.picking_id:
                item["picking_ids"].add(move.picking_id.id)

        by_product = defaultdict(list)
        for item in aggregates.values():
            product = item["line"].product_id
            if not item["date"] or float_compare(
                item["qty"], 0.0, precision_rounding=product.uom_id.rounding
            ) <= 0:
                continue
            line = item["line"]
            unit_price = line._get_gross_price_unit()
            conversion_date = fields.Date.context_today(self, item["date"])
            item["price"] = line.currency_id._convert(
                unit_price,
                self.company_id.currency_id,
                self.company_id,
                conversion_date,
                round=False,
            )
            by_product[product.id].append(item)
        for items in by_product.values():
            items.sort(key=lambda x: (x["date"], x["line"].id), reverse=True)
        return by_product

    def _purchase_values(self, number, item):
        line = item["line"]
        prefix = f"purchase_{number}_"
        return {
            f"purchase_{number}_id": line.order_id.id,
            f"purchase_{number}_line_id": line.id,
            f"purchase_{number}_partner_id": line.order_id.partner_id.id,
            f"purchase_{number}_date": item["date"],
            f"purchase_{number}_qty": item["qty"],
            f"purchase_{number}_price": item["price"],
            f"purchase_{number}_receipt_ids": [Command.set(item["picking_ids"])],
        }

    def action_calculate(self):
        self.ensure_one()
        if self.state not in ("draft", "calculated"):
            raise UserError(_("Solo se puede calcular un cierre borrador o calculado."))
        if self.company_id not in self.env.companies:
            raise AccessError(_("La compañía del cierre no está habilitada para el usuario."))

        purchase_limit = self._get_setting_int(
            "indoor_costos_estandar.purchase_count", 3, minimum=1, maximum=3
        )
        stale_days = self._get_setting_int("indoor_costos_estandar.stale_days", 180)
        warning_threshold = self._get_setting_float(
            "indoor_costos_estandar.warning_threshold", 10.0
        )
        critical_threshold = self._get_setting_float(
            "indoor_costos_estandar.critical_threshold", 20.0
        )
        if critical_threshold < warning_threshold:
            raise ValidationError(_("El umbral crítico no puede ser menor al de advertencia."))

        company = self.company_id
        cutoff = fields.Datetime.to_string(datetime.combine(self.closing_date, time.max))
        products = self.env["product.product"].with_company(company).search(
            [
                ("use_monthly_standard_cost", "=", True),
                ("is_storable", "=", True),
            ]
        )
        candidates = self._prepare_purchase_candidates(products, cutoff)
        historical_products = products.with_context(to_date=cutoff)
        stock_by_product = {product.id: product.qty_available for product in historical_products}

        self.line_ids.unlink()
        line_values = []
        today = self.closing_date
        for product in products:
            product = product.with_company(company)
            stock_qty = stock_by_product.get(product.id, 0.0)
            old_price = product.standard_price
            items = candidates.get(product.id, [])[:purchase_limit]
            total_qty = sum(item["qty"] for item in items)
            total_value = sum(item["qty"] * item["price"] for item in items)
            calculated = total_value / total_qty if total_qty else old_price
            warnings = []
            status = "ready"
            if product.cost_method != "standard":
                status = "invalid_method"
                warnings.append(_("El producto no utiliza método de costo estándar."))
            if float_compare(stock_qty, 0.0, precision_rounding=product.uom_id.rounding) < 0:
                status = "negative_stock"
                warnings.append(_("Stock negativo: corrija la existencia antes de aplicar."))
            if not items:
                if status == "ready":
                    status = "no_purchase"
                warnings.append(_("Sin compras disponibles para recalcular costo."))
            elif (today - fields.Date.context_today(self, items[0]["date"])).days > stale_days:
                if status == "ready":
                    status = "stale"
                warnings.append(_("La última compra supera %s días.", stale_days))

            vals = {
                "batch_id": self.id,
                "product_id": product.id,
                "uom_id": product.uom_id.id,
                "stock_qty": stock_qty,
                "old_standard_price": old_price,
                "stock_value_before": stock_qty * old_price,
                "total_purchase_qty": total_qty,
                "total_purchase_value": total_value,
                "purchase_count": len(items),
                "calculated_standard_price": calculated,
                "approved_standard_price": calculated,
                "validation_status": status,
                "warning": "\n".join(warnings),
            }
            for number, item in enumerate(items, start=1):
                vals.update(self._purchase_values(number, item))
            line_values.append(vals)

        self.env["indoor.standard.cost.line"].create(line_values)
        now = fields.Datetime.now()
        self.write(
            {
                "state": "calculated",
                "calculation_date": now,
                "calculated_by": self.env.user.id,
                "calculated_at": now,
                "purchase_limit": purchase_limit,
                "stale_days": stale_days,
                "warning_threshold": warning_threshold,
                "critical_threshold": critical_threshold,
            }
        )
        for line in self.line_ids:
            line.product_id.with_company(company).write(
                {
                    "last_standard_cost_calculation_date": self.closing_date,
                    "last_calculated_standard_cost": line.calculated_standard_price,
                    "last_approved_standard_cost": line.approved_standard_price,
                }
            )
        self.message_post(body=_("Cálculo realizado: %s productos.", len(line_values)))
        return True

    def action_include_eligible_products(self):
        """Explicitly opt in all storable standard-cost templates for this company."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Solo se pueden incluir productos en un cierre borrador."))
        templates = self.env["product.template"].with_company(self.company_id).search(
            [
                ("is_storable", "=", True),
                ("cost_method", "=", "standard"),
                ("use_monthly_standard_cost", "=", False),
            ]
        )
        templates.write({"use_monthly_standard_cost": True})
        self.message_post(
            body=_("Se incorporaron %s productos elegibles a la política de costo mensual.", len(templates))
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Productos incluidos"),
                "message": _("Se marcaron %s productos almacenables con costo estándar.", len(templates)),
                "type": "success",
                "sticky": False,
            },
        }

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group("indoor_inventario.group_standard_cost_approver"):
            raise AccessError(_("Solo un aprobador de costos puede aprobar el cierre."))
        if self.state != "calculated":
            raise UserError(_("Solo se puede aprobar un cierre calculado."))
        if not self.line_ids:
            raise UserError(_("El cierre no contiene productos."))
        now = fields.Datetime.now()
        self.write({"state": "approved", "approved_by": self.env.user.id, "approved_at": now})
        for line in self.line_ids:
            line.product_id.with_company(self.company_id).last_approved_standard_cost = line.approved_standard_price
        self.message_post(body=_("Aprobado por %s.", self.env.user.display_name))
        return True

    def action_apply(self):
        self.ensure_one()
        if not self.env.user.has_group("indoor_inventario.group_standard_cost_approver"):
            raise AccessError(_("Solo un aprobador de costos puede aplicar costos."))
        if self.state != "approved":
            raise UserError(_("Solo se puede aplicar un cierre aprobado."))
        duplicate = self.search_count(
            [
                ("id", "!=", self.id),
                ("company_id", "=", self.company_id.id),
                ("closing_date", "=", self.closing_date),
                ("state", "=", "applied"),
            ]
        )
        if duplicate:
            raise ValidationError(_("Ya existe un cierre aplicado para esta compañía y fecha."))
        blocked = self.line_ids.filtered(lambda line: line.validation_status == "negative_stock")
        if blocked:
            raise ValidationError(
                _("No se puede aplicar: hay %s producto(s) con stock negativo.", len(blocked))
            )

        applicable = self.line_ids.filtered(
            lambda line: line.validation_status != "invalid_method"
            and line.product_id.with_company(self.company_id).cost_method == "standard"
        )
        updated_count = 0
        for line in applicable:
            product = line.product_id.with_company(self.company_id)
            if not float_is_zero(
                product.standard_price - line.approved_standard_price,
                precision_digits=self.env["decimal.precision"].precision_get("Product Price"),
            ):
                product.write({"standard_price": line.approved_standard_price})
                updated_count += 1
            product.write(
                {
                    "last_standard_cost_application_date": self.closing_date,
                    "last_approved_standard_cost": line.approved_standard_price,
                }
            )
        now = fields.Datetime.now()
        self.write({"state": "applied", "applied_by": self.env.user.id, "applied_at": now})
        self.message_post(
            body=_(
                "Costos aplicados. Productos actualizados: %(count)s; valor anterior: %(before)s; "
                "valor nuevo: %(after)s; variación: %(difference)s.",
                count=updated_count,
                before=sum(applicable.mapped("stock_value_before")),
                after=sum(applicable.mapped("stock_value_after")),
                difference=sum(applicable.mapped("revaluation_difference")),
            )
        )
        return True

    def action_cancel(self):
        for batch in self:
            if batch.state == "applied":
                raise UserError(_("Un cierre aplicado no se puede cancelar."))
            batch.state = "cancelled"
        return True

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No hay líneas para exportar."))
        return {
            "type": "ir.actions.act_url",
            "url": "/indoor_inventario/standard_cost_batch/%s/xlsx" % self.id,
            "target": "download",
        }

    def _get_xlsx_content(self):
        """Build the spreadsheet shown in the batch review grid."""
        self.ensure_one()
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Costos estándar")

        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#714B67",
                "font_color": "#FFFFFF",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        text_format = workbook.add_format({"border": 1})
        number_format = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        percent_format = workbook.add_format({"border": 1, "num_format": "0.00\"%\""})

        columns = [
            ("Producto", "product_id", "text", 32),
            ("Categoría", "product_category_id", "text", 28),
            ("Cantidad stock", "stock_qty", "number", 14),
            ("PPM anterior", "old_standard_price", "number", 14),
            ("Cant 1", "purchase_1_qty", "number", 11),
            ("Precio 1", "purchase_1_price", "number", 13),
            ("Cant 2", "purchase_2_qty", "number", 11),
            ("Precio 2", "purchase_2_price", "number", 13),
            ("Cant 3", "purchase_3_qty", "number", 11),
            ("Precio 3", "purchase_3_price", "number", 13),
            ("PPM", "calculated_standard_price", "number", 13),
            ("PPM Aprobado", "approved_standard_price", "number", 15),
            ("Diferencia $", "absolute_difference", "number", 14),
            ("Diferencia %", "percentage_difference", "percent", 14),
            ("Nuevo Inventario", "stock_value_after", "number", 18),
            ("Diferencia Inventario", "revaluation_difference", "number", 21),
            ("Estado", "validation_status", "selection", 16),
            ("Alerta", "warning", "text", 42),
        ]
        status_labels = dict(
            self.env["indoor.standard.cost.line"]._fields["validation_status"].selection
        )

        for column_index, (label, _field_name, _kind, width) in enumerate(columns):
            worksheet.write(0, column_index, label, header_format)
            worksheet.set_column(column_index, column_index, width)

        for row_index, line in enumerate(self.line_ids, start=1):
            for column_index, (_label, field_name, kind, _width) in enumerate(columns):
                value = line[field_name]
                if kind == "text":
                    value = value.display_name if hasattr(value, "display_name") else (value or "")
                    worksheet.write(row_index, column_index, value, text_format)
                elif kind == "selection":
                    worksheet.write(
                        row_index,
                        column_index,
                        status_labels.get(value, value or ""),
                        text_format,
                    )
                else:
                    worksheet.write_number(
                        row_index,
                        column_index,
                        value or 0.0,
                        percent_format if kind == "percent" else number_format,
                    )

        worksheet.freeze_panes(1, 2)
        worksheet.autofilter(0, 0, len(self.line_ids), len(columns) - 1)
        worksheet.set_row(0, 30)
        workbook.close()
        return output.getvalue()
