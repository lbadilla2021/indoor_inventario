from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "indoor_receipt_details")
class TestReceiptDetails(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Proveedor recepción test", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto recepción test",
                "is_storable": True,
                "purchase_ok": True,
            }
        )

    def test_receipt_exposes_purchase_price_invoice_and_modal_action(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 3.0,
                "product_uom": self.product.uom_po_id.id,
                "price_unit": 123.45,
            }
        )
        order.button_confirm()
        picking = order.picking_ids[:1]
        move = picking.move_ids.filtered(lambda item: item.product_id == self.product)[:1]

        self.assertEqual(move.purchase_price_unit, 123.45)
        self.assertEqual(move.purchase_currency_id, order.currency_id)
        move.vendor_invoice_ref = "FAC-TEST-001"
        self.assertEqual(move.vendor_invoice_ref, "FAC-TEST-001")

        action = picking.action_open_purchase_order_modal()
        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(action["res_id"], order.id)
        self.assertEqual(action["target"], "new")
        self.assertFalse(action["context"]["edit"])
