from datetime import datetime, time, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    use_monthly_standard_cost = fields.Boolean(
        string="Usar costo estándar mensual",
        help="El costo se revisa y aplica mediante el cierre mensual de costos estándar.",
    )
    last_standard_cost_calculation_date = fields.Date(
        string="Fecha último cálculo", compute="_compute_monthly_cost_summary"
    )
    last_standard_cost_application_date = fields.Date(
        string="Fecha última aplicación", compute="_compute_monthly_cost_summary"
    )
    last_calculated_standard_cost = fields.Float(
        string="Último costo calculado", digits="Product Price",
        compute="_compute_monthly_cost_summary",
    )
    last_approved_standard_cost = fields.Float(
        string="Último costo aprobado", digits="Product Price",
        compute="_compute_monthly_cost_summary",
    )
    standard_cost_history_count = fields.Integer(compute="_compute_monthly_cost_summary")
    indoor_is_immobilized = fields.Boolean(
        string="Inmovilizado",
        readonly=True,
        copy=False,
        index=True,
        help=(
            "Se marca automáticamente cuando el último consumo hacia Producción/Consumo "
            "materiales supera la antigüedad configurada."
        ),
    )
    indoor_last_consumption_date = fields.Datetime(
        string="Último consumo en producción",
        readonly=True,
        copy=False,
        index=True,
    )

    def _compute_monthly_cost_summary(self):
        for template in self:
            variants = template.product_variant_ids.with_company(self.env.company)
            latest = variants.sorted(
                key=lambda product: product.last_standard_cost_calculation_date or fields.Date.from_string("1900-01-01"),
                reverse=True,
            )[:1]
            template.last_standard_cost_calculation_date = latest.last_standard_cost_calculation_date
            template.last_standard_cost_application_date = latest.last_standard_cost_application_date
            template.last_calculated_standard_cost = latest.last_calculated_standard_cost
            template.last_approved_standard_cost = latest.last_approved_standard_cost
            template.standard_cost_history_count = self.env["indoor.standard.cost.line"].search_count(
                [("product_id", "in", variants.ids)]
            )

    def action_view_standard_cost_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "indoor_inventario.action_standard_cost_line_history"
        )
        action["domain"] = [("product_id.product_tmpl_id", "=", self.id)]
        return action

    @api.model
    def _get_immobilization_months(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "indoor_inventario.immobilization_months", "6"
        )
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 6

    @api.model
    def action_update_immobilized_products(self):
        """Refresh the reversible immobilized flag from completed consumptions."""
        self.env["stock.location"]._setup_indoor_production_delivery()
        consumption_locations = self.env["stock.location"].sudo().search(
            [("indoor_is_material_consumption", "=", True)]
        )
        stock_locations = self.env["stock.warehouse"].sudo().search([]).mapped("lot_stock_id")
        products = self.sudo().with_context(active_test=False).search(
            [("is_storable", "=", True)]
        )

        latest_by_template = {}
        if consumption_locations and stock_locations and products:
            grouped_moves = self.env["stock.move"].sudo()._read_group(
                [
                    ("state", "=", "done"),
                    ("product_id.product_tmpl_id", "in", products.ids),
                    ("location_id", "child_of", stock_locations.ids),
                    ("location_dest_id", "child_of", consumption_locations.ids),
                ],
                ["product_id"],
                ["date:max"],
            )
            for product, last_date in grouped_moves:
                template_id = product.product_tmpl_id.id
                if last_date and (
                    template_id not in latest_by_template
                    or last_date > latest_by_template[template_id]
                ):
                    latest_by_template[template_id] = last_date

        cutoff = fields.Datetime.now() - relativedelta(
            months=self._get_immobilization_months()
        )
        marked = released = 0
        for product in products:
            last_date = latest_by_template.get(product.id)
            should_be_immobilized = bool(last_date and last_date < cutoff)
            if product.indoor_is_immobilized != should_be_immobilized:
                marked += int(should_be_immobilized)
                released += int(not should_be_immobilized)
            values = {"indoor_is_immobilized": should_be_immobilized}
            if product.indoor_last_consumption_date != last_date:
                values["indoor_last_consumption_date"] = last_date or False
            if (
                product.indoor_is_immobilized != should_be_immobilized
                or "indoor_last_consumption_date" in values
            ):
                product.write(values)

        return {
            "evaluated": len(products),
            "immobilized": sum(products.mapped("indoor_is_immobilized")),
            "marked": marked,
            "released": released,
        }

    @api.model
    def _cron_update_immobilized_products(self):
        self.action_update_immobilized_products()
        self._schedule_immobilized_products_cron()
        return True

    @api.model
    def _schedule_immobilized_products_cron(self):
        """Set the next execution to 03:00 in the company's local time zone."""
        cron = self.env.ref(
            "indoor_inventario.ir_cron_update_immobilized_products",
            raise_if_not_found=False,
        )
        if not cron:
            return False
        timezone_name = self.env.company.partner_id.tz or self.env.user.tz
        if not timezone_name:
            company_user = self.env["res.users"].sudo().search(
                [
                    ("active", "=", True),
                    ("company_ids", "in", self.env.company.id),
                    ("partner_id.tz", "!=", False),
                ],
                order="id",
                limit=1,
            )
            timezone_name = company_user.tz
        timezone_name = timezone_name or "UTC"
        try:
            local_timezone = pytz.timezone(timezone_name)
        except pytz.UnknownTimeZoneError:
            local_timezone = pytz.UTC
        now_utc = pytz.UTC.localize(fields.Datetime.now())
        now_local = now_utc.astimezone(local_timezone)
        run_date = now_local.date()
        if now_local.time() >= time(hour=3):
            run_date += timedelta(days=1)
        next_local = local_timezone.localize(datetime.combine(run_date, time(hour=3)))
        cron.sudo().write(
            {"nextcall": next_local.astimezone(pytz.UTC).replace(tzinfo=None)}
        )
        return True


class ProductProduct(models.Model):
    _inherit = "product.product"

    use_monthly_standard_cost = fields.Boolean(
        related="product_tmpl_id.use_monthly_standard_cost", store=True, readonly=True
    )
    last_standard_cost_calculation_date = fields.Date(
        string="Fecha último cálculo", company_dependent=True, readonly=True
    )
    last_standard_cost_application_date = fields.Date(
        string="Fecha última aplicación", company_dependent=True, readonly=True
    )
    last_calculated_standard_cost = fields.Float(
        string="Último costo calculado", digits="Product Price",
        company_dependent=True, readonly=True,
    )
    last_approved_standard_cost = fields.Float(
        string="Último costo aprobado", digits="Product Price",
        company_dependent=True, readonly=True,
    )
    standard_cost_history_count = fields.Integer(
        compute="_compute_standard_cost_history_count"
    )
    indoor_is_immobilized = fields.Boolean(
        related="product_tmpl_id.indoor_is_immobilized",
        string="Inmovilizado",
        store=True,
        readonly=True,
    )
    indoor_last_consumption_date = fields.Datetime(
        related="product_tmpl_id.indoor_last_consumption_date",
        string="Último consumo en producción",
        store=True,
        readonly=True,
    )

    def _compute_standard_cost_history_count(self):
        grouped = self.env["indoor.standard.cost.line"]._read_group(
            [("product_id", "in", self.ids)], ["product_id"], ["__count"]
        )
        counts = {product.id: count for product, count in grouped}
        for product in self:
            product.standard_cost_history_count = counts.get(product.id, 0)

    def action_view_standard_cost_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "indoor_inventario.action_standard_cost_line_history"
        )
        action["domain"] = [("product_id", "=", self.id)]
        action["context"] = {"default_product_id": self.id}
        return action
