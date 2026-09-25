from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    indoor_standard_cost_purchase_count = fields.Integer(
        string="Compras consideradas",
        default=3,
        config_parameter="indoor_costos_estandar.purchase_count",
    )
    indoor_standard_cost_stale_days = fields.Integer(
        string="Compra obsoleta después de (días)",
        default=180,
        config_parameter="indoor_costos_estandar.stale_days",
    )
    indoor_standard_cost_warning_threshold = fields.Float(
        string="Umbral de advertencia (%)",
        default=10.0,
        config_parameter="indoor_costos_estandar.warning_threshold",
    )
    indoor_standard_cost_critical_threshold = fields.Float(
        string="Umbral crítico (%)",
        default=20.0,
        config_parameter="indoor_costos_estandar.critical_threshold",
    )
    indoor_immobilization_months = fields.Integer(
        string="Meses sin consumo para inmovilizar",
        default=6,
        config_parameter="indoor_inventario.immobilization_months",
        help=(
            "Un producto se marca como inmovilizado cuando su último movimiento terminado "
            "desde una bodega hacia Producción/Consumo materiales supera este plazo."
        ),
    )

    @api.constrains("indoor_immobilization_months")
    def _check_indoor_immobilization_months(self):
        for settings in self:
            if settings.indoor_immobilization_months < 1:
                raise ValidationError(_("La cantidad de meses debe ser mayor o igual a 1."))

    def action_update_immobilized_products(self):
        self.ensure_one()
        self.execute()
        result = self.env["product.template"].action_update_immobilized_products()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Productos inmovilizados actualizados"),
                "message": _(
                    "Productos revisados: %(evaluated)s. Inmovilizados: %(immobilized)s. "
                    "Marcados ahora: %(marked)s. Liberados ahora: %(released)s.",
                    **result,
                ),
                "type": "success",
                "sticky": False,
            },
        }
