from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indoor_provisional_product")
class TestProvisionalProduct(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env["product.category"].create(
            {"name": "Producto provisional test"}
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente y proveedor provisional test",
                "customer_rank": 1,
                "supplier_rank": 1,
            }
        )

    def _create_provisional(self, name):
        return self.env["indoor.provisional.product"].create(
            {"name": name, "categ_id": self.category.id}
        )

    def test_sale_confirmation_converts_and_replaces_provisional(self):
        provisional = self._create_provisional("Bien provisional venta")
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "provisional_product_id": provisional.id,
                "product_uom_qty": 2.0,
                "price_unit": 500.0,
            }
        )
        self.assertEqual(line.product_id, provisional._get_placeholder_product())
        self.assertEqual(provisional.state, "quoted")

        order.action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertEqual(provisional.state, "converted")
        self.assertEqual(line.product_id, provisional.definitive_product_id)
        self.assertTrue(line.product_id.is_storable)
        self.assertTrue(line.product_id.sale_ok)
        self.assertTrue(line.product_id.purchase_ok)
        self.assertEqual(line.product_id.route_ids, provisional.route_id)

    def test_purchase_confirmation_sets_cost_and_replaces_provisional(self):
        provisional = self._create_provisional("Bien provisional compra")
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "provisional_product_id": provisional.id,
                "product_qty": 4.0,
                "price_unit": 250.0,
            }
        )
        self.assertEqual(line.product_id, provisional._get_placeholder_product())
        self.assertEqual(provisional.state, "quoted")

        order.button_confirm()

        self.assertEqual(order.state, "purchase")
        self.assertEqual(provisional.state, "converted")
        self.assertEqual(line.product_id, provisional.definitive_product_id)
        self.assertEqual(provisional.cost, 250.0)
        self.assertEqual(
            provisional.definitive_product_id.with_company(order.company_id).standard_price,
            250.0,
        )

    def test_placeholder_name_visibility_and_required_provisional(self):
        placeholder = self.env[
            "indoor.provisional.product"
        ]._get_placeholder_product()
        self.assertEqual(placeholder.display_name, "Producto Provisional")
        self.assertTrue(placeholder.active)

        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": placeholder.id,
                "product_qty": 1.0,
                "price_unit": 100.0,
            }
        )
        self.assertTrue(line.is_provisional_placeholder)
        with self.assertRaises(UserError):
            order.button_confirm()
