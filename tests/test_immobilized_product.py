from dateutil.relativedelta import relativedelta
import pytz

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indoor_immobilized_product")
class TestImmobilizedProduct(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.env["stock.location"]._setup_indoor_production_delivery(cls.warehouse)
        cls.consumption_location = cls.env["stock.location"].search(
            [
                ("indoor_is_material_consumption", "=", True),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        cls.picking_type = cls.env["stock.picking.type"].search(
            [
                ("indoor_is_production_delivery", "=", True),
                ("warehouse_id", "=", cls.warehouse.id),
            ],
            limit=1,
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Material con control de inmovilización", "is_storable": True}
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "indoor_inventario.immobilization_months", 6
        )

    def _create_done_consumption(self, date):
        move = self.env["stock.move"].create(
            {
                "name": "Consumo de prueba",
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "product_uom": self.product.uom_id.id,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": self.consumption_location.id,
                "picking_type_id": self.picking_type.id,
                "state": "done",
                "date": date,
            }
        )
        return move

    def test_setup_is_idempotent_and_ready(self):
        self.assertTrue(self.consumption_location)
        self.assertEqual(self.consumption_location.usage, "production")
        self.assertEqual(
            self.picking_type.default_location_src_id, self.warehouse.lot_stock_id
        )
        self.assertEqual(
            self.picking_type.default_location_dest_id, self.consumption_location
        )
        location_count = self.env["stock.location"].search_count(
            [
                ("indoor_is_material_consumption", "=", True),
                ("company_id", "=", self.env.company.id),
            ]
        )
        picking_type_count = self.env["stock.picking.type"].search_count(
            [
                ("indoor_is_production_delivery", "=", True),
                ("warehouse_id", "=", self.warehouse.id),
            ]
        )
        self.env["stock.location"]._setup_indoor_production_delivery(self.warehouse)
        self.assertEqual(
            self.env["stock.location"].search_count(
                [
                    ("indoor_is_material_consumption", "=", True),
                    ("company_id", "=", self.env.company.id),
                ]
            ),
            location_count,
        )
        self.assertEqual(
            self.env["stock.picking.type"].search_count(
                [
                    ("indoor_is_production_delivery", "=", True),
                    ("warehouse_id", "=", self.warehouse.id),
                ]
            ),
            picking_type_count,
        )

    def test_old_consumption_marks_and_recent_consumption_releases(self):
        old_date = fields.Datetime.now() - relativedelta(months=7)
        self._create_done_consumption(old_date)
        self.env["product.template"].action_update_immobilized_products()
        self.assertTrue(self.product.product_tmpl_id.indoor_is_immobilized)
        self.assertEqual(
            self.product.product_tmpl_id.indoor_last_consumption_date, old_date
        )

        recent_date = fields.Datetime.now() - relativedelta(months=1)
        self._create_done_consumption(recent_date)
        self.env["product.template"].action_update_immobilized_products()
        self.assertFalse(self.product.product_tmpl_id.indoor_is_immobilized)
        self.assertEqual(
            self.product.product_tmpl_id.indoor_last_consumption_date, recent_date
        )

    def test_product_without_consumption_is_not_immobilized(self):
        self.product.product_tmpl_id.indoor_is_immobilized = True
        self.env["product.template"].action_update_immobilized_products()
        self.assertFalse(self.product.product_tmpl_id.indoor_is_immobilized)
        self.assertFalse(self.product.product_tmpl_id.indoor_last_consumption_date)

    def test_cron_is_scheduled_at_three_company_time(self):
        self.env.company.partner_id.tz = "America/Santiago"
        self.env["product.template"]._schedule_immobilized_products_cron()
        cron = self.env.ref("indoor_inventario.ir_cron_update_immobilized_products")
        nextcall_utc = pytz.UTC.localize(cron.nextcall)
        self.assertEqual(
            nextcall_utc.astimezone(pytz.timezone("America/Santiago")).hour,
            3,
        )
