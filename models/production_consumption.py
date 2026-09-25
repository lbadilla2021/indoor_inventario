from odoo import api, fields, models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    @api.model
    def _sync_indoor_inventory_display_name(self):
        module = self.sudo().search([("name", "=", "indoor_inventario")], limit=1)
        if not module:
            return False
        languages = self.env["res.lang"].sudo().with_context(active_test=False).search(
            [("active", "=", True)]
        )
        module.with_context(lang="en_US").write({"shortdesc": "Indoor Inventario"})
        for language in languages:
            module.with_context(lang=language.code).write(
                {"shortdesc": "Indoor Inventario"}
            )
        return True


class StockLocation(models.Model):
    _inherit = "stock.location"

    indoor_is_material_consumption = fields.Boolean(
        string="Consumo de materiales Indoor",
        default=False,
        copy=False,
        index=True,
    )
    indoor_is_production_root = fields.Boolean(
        string="Raíz de producción Indoor",
        default=False,
        copy=False,
        index=True,
    )

    @api.model
    def _setup_indoor_production_delivery(self, warehouses=None):
        """Create missing consumption locations and operation types without deleting data."""
        parameters = self.env["ir.config_parameter"].sudo()
        if not parameters.get_param("indoor_inventario.immobilization_months"):
            parameters.set_param("indoor_inventario.immobilization_months", 6)
        warehouses = warehouses or self.env["stock.warehouse"].sudo().search([])
        virtual_root = self.env.ref("stock.stock_location_locations_virtual")
        PickingType = self.env["stock.picking.type"].sudo()
        Location = self.sudo()

        for warehouse in warehouses:
            company = warehouse.company_id
            production_root = Location.search(
                [
                    ("indoor_is_production_root", "=", True),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not production_root:
                production_root = Location.search(
                    [
                        ("name", "in", ["Producción", "Production"]),
                        ("location_id", "=", virtual_root.id),
                        ("usage", "=", "view"),
                        ("company_id", "in", [False, company.id]),
                    ],
                    limit=1,
                )
            if not production_root:
                production_root = Location.create(
                    {
                        "name": "Producción",
                        "location_id": virtual_root.id,
                        "usage": "view",
                        "company_id": company.id,
                        "indoor_is_production_root": True,
                    }
                )
            elif not production_root.indoor_is_production_root:
                production_root.indoor_is_production_root = True

            consumption = Location.search(
                [
                    ("indoor_is_material_consumption", "=", True),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not consumption:
                consumption = Location.search(
                    [
                        ("name", "=", "Consumo materiales"),
                        ("location_id", "=", production_root.id),
                        ("usage", "=", "production"),
                        ("company_id", "in", [False, company.id]),
                    ],
                    limit=1,
                )
            if not consumption:
                consumption = Location.create(
                    {
                        "name": "Consumo materiales",
                        "location_id": production_root.id,
                        "usage": "production",
                        "company_id": company.id,
                        "indoor_is_material_consumption": True,
                    }
                )
            elif not consumption.indoor_is_material_consumption:
                consumption.indoor_is_material_consumption = True

            picking_type = PickingType.search(
                [
                    ("indoor_is_production_delivery", "=", True),
                    ("warehouse_id", "=", warehouse.id),
                ],
                limit=1,
            )
            if not picking_type:
                picking_type = PickingType.search(
                    [
                        ("name", "=", "Entrega a Producción"),
                        ("code", "=", "internal"),
                        ("warehouse_id", "=", warehouse.id),
                    ],
                    limit=1,
                )
            values = {
                "name": "Entrega a Producción",
                "code": "internal",
                "sequence_code": "PROD",
                "warehouse_id": warehouse.id,
                "company_id": company.id,
                "default_location_src_id": warehouse.lot_stock_id.id,
                "default_location_dest_id": consumption.id,
                "indoor_is_production_delivery": True,
                "active": True,
            }
            if picking_type:
                picking_type.write(values)
            else:
                PickingType.create(values)
        return True


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    indoor_is_production_delivery = fields.Boolean(
        string="Entrega a Producción Indoor",
        default=False,
        copy=False,
        index=True,
    )


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model_create_multi
    def create(self, vals_list):
        warehouses = super().create(vals_list)
        self.env["stock.location"]._setup_indoor_production_delivery(warehouses)
        return warehouses
