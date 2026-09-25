from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indoor_inventory_count")
class TestInventoryCount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto para inventariar",
                "is_storable": True,
                "barcode": "INDOOR-COUNT-001",
            }
        )

    def test_lines_start_session_and_build_consolidated(self):
        session = self.env["indoor.inventory.count.session"].create(
            {"location_id": self.warehouse.lot_stock_id.id}
        )
        Line = self.env["indoor.inventory.count.line"]
        Line.create(
            {
                "session_id": session.id,
                "location_id": session.location_id.id,
                "product_id": self.product.id,
                "quantity": 2,
            }
        )
        Line.create(
            {
                "session_id": session.id,
                "location_id": session.location_id.id,
                "product_id": self.product.id,
                "quantity": 3,
            }
        )

        self.assertEqual(session.state, "in_progress")
        consolidated = self.env["indoor.inventory.count.consolidated"].search(
            [("session_id", "=", session.id), ("product_id", "=", self.product.id)]
        )
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated.counted_quantity, 5)
        self.assertEqual(consolidated.scan_count, 2)

    def test_barcode_onchange_selects_product(self):
        line = self.env["indoor.inventory.count.line"].new(
            {"barcode": "INDOOR-COUNT-001"}
        )
        warning = line._onchange_barcode()
        self.assertFalse(warning)
        self.assertEqual(line.product_id, self.product)

    def test_menu_positions_and_actions_are_indoor_owned(self):
        inventory_menu = self.env.ref("indoor_inventario.menu_inventory_count")
        session_menu = self.env.ref(
            "indoor_inventario.menu_inventory_count_session"
        )
        consolidated_menu = self.env.ref(
            "indoor_inventario.menu_inventory_count_consolidated"
        )
        self.assertEqual(inventory_menu.parent_id, self.env.ref("stock.menu_stock_root"))
        self.assertEqual(inventory_menu.name, "Inventariar")
        self.assertEqual(
            session_menu.parent_id, self.env.ref("stock.menu_stock_warehouse_mgmt")
        )
        self.assertLess(
            session_menu.sequence, self.env.ref("stock.menu_stock_procurement").sequence
        )
        self.assertEqual(
            consolidated_menu.parent_id, self.env.ref("stock.menu_warehouse_report")
        )
        self.assertGreater(
            consolidated_menu.sequence,
            self.env.ref("stock.stock_move_line_menu").sequence,
        )
        self.assertEqual(
            inventory_menu.action.res_model, "indoor.inventory.count.line"
        )
        self.assertEqual(
            session_menu.action.res_model, "indoor.inventory.count.session"
        )
        self.assertEqual(
            consolidated_menu.action.res_model,
            "indoor.inventory.count.consolidated",
        )

    def test_custom_label_report_is_indoor_owned(self):
        report = self.env.ref("indoor_inventario.action_report_product_label_custom")
        self.assertEqual(
            report.report_name,
            "indoor_inventario.report_producttemplatelabel_custom",
        )
        self.assertTrue(
            self.env.ref("indoor_inventario.report_producttemplatelabel_custom")
        )
