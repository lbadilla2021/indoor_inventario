from datetime import datetime, time, timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools.float_utils import float_compare
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data


@tagged("post_install", "-at_install", "indoor_standard_cost")
class TestStandardCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.env.user.groups_id = [
            Command.link(cls.env.ref("indoor_inventario.group_standard_cost_approver").id)
        ]
        cls.category = cls.env["product.category"].create(
            {"name": "Costo estándar test", "property_cost_method": "standard", "property_valuation": "manual_periodic"}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto costo mensual",
                "is_storable": True,
                "categ_id": cls.category.id,
                "standard_price": 100.0,
            }
        )
        cls.product.product_tmpl_id.use_monthly_standard_cost = True
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor test"})
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.closing_date = fields.Date.today()

    def _date(self, days_before=0):
        return datetime.combine(self.closing_date - timedelta(days=days_before), time(12, 0))

    def _finish_move(self, move, qty):
        move._action_confirm()
        move._action_assign()
        if move.move_line_ids:
            move.move_line_ids.quantity = qty
        else:
            self.env["stock.move.line"].create(
                {
                    "move_id": move.id,
                    "product_id": move.product_id.id,
                    "product_uom_id": move.product_uom.id,
                    "quantity": qty,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                }
            )
        move.picked = True
        move._action_done()

    def _purchase_receipt(self, qty, price, date, product=None, uom=None, currency=None, state="purchase"):
        product = product or self.product
        uom = uom or product.uom_id
        currency = currency or self.company.currency_id
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "company_id": self.company.id,
                "currency_id": currency.id,
                "date_order": date,
            }
        )
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": product.id,
                "name": product.display_name,
                "product_qty": qty,
                "product_uom": uom.id,
                "price_unit": price,
                "date_planned": date,
            }
        )
        order.write({"state": state})
        if state == "cancel":
            return order, line, self.env["stock.move"]
        move = self.env["stock.move"].create(
            {
                "name": line.name,
                "product_id": product.id,
                "product_uom_qty": qty,
                "product_uom": uom.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "company_id": self.company.id,
                "purchase_line_id": line.id,
            }
        )
        self._finish_move(move, qty)
        move.date = date
        return order, line, move

    def _calculate(self, product=None, closing=None):
        batch = self.env["indoor.standard.cost.batch"].create(
            {"company_id": self.company.id, "closing_date": closing or self.closing_date}
        )
        batch.action_calculate()
        return batch, batch.line_ids.filtered(lambda line: line.product_id == (product or self.product))

    def test_01_three_weighted_purchases(self):
        self._purchase_receipt(500, 1500, self._date(60))
        self._purchase_receipt(1000, 1600, self._date(30))
        self._purchase_receipt(200, 1800, self._date(2))
        _batch, line = self._calculate()
        expected = (500 * 1500 + 1000 * 1600 + 200 * 1800) / 1700
        self.assertEqual(line.purchase_count, 3)
        price_digits = self.env["decimal.precision"].precision_get("Product Price")
        self.assertEqual(float_compare(line.calculated_standard_price, expected, precision_digits=price_digits), 0)

    def test_02_two_purchases(self):
        self._purchase_receipt(2, 100, self._date(30))
        self._purchase_receipt(1, 160, self._date(2))
        _batch, line = self._calculate()
        self.assertEqual(line.purchase_count, 2)
        self.assertAlmostEqual(line.calculated_standard_price, 120.0)

    def test_03_one_purchase(self):
        self._purchase_receipt(4, 175, self._date(2))
        _batch, line = self._calculate()
        self.assertEqual(line.purchase_count, 1)
        self.assertAlmostEqual(line.calculated_standard_price, 175.0)

    def test_04_no_purchase_keeps_old_cost(self):
        _batch, line = self._calculate()
        self.assertEqual(line.validation_status, "no_purchase")
        self.assertEqual(line.calculated_standard_price, 100.0)

    def test_05_partial_receipt_uses_done_quantity(self):
        order, line, _move = self._purchase_receipt(600, 50, self._date(2))
        line.product_qty = 1000
        _batch, result = self._calculate()
        self.assertEqual(result.purchase_1_qty, 600)

    def test_06_cancelled_purchase_is_ignored(self):
        self._purchase_receipt(10, 999, self._date(2), state="cancel")
        _batch, line = self._calculate()
        self.assertEqual(line.purchase_count, 0)

    def test_07_future_receipt_is_ignored(self):
        self._purchase_receipt(10, 999, self._date(-1))
        _batch, line = self._calculate()
        self.assertEqual(line.purchase_count, 0)

    def test_08_different_uom_is_normalized(self):
        box = self.env["uom.uom"].create(
            {"name": "Caja 100", "category_id": self.product.uom_id.category_id.id, "uom_type": "bigger", "factor_inv": 100}
        )
        self._purchase_receipt(2, 1000, self._date(2), uom=box)
        _batch, line = self._calculate()
        self.assertEqual(line.purchase_1_qty, 200)
        self.assertAlmostEqual(line.purchase_1_price, 10.0)

    def test_09_foreign_currency_uses_odoo_conversion(self):
        usd = self.env["res.currency"].with_context(active_test=False).search(
            [("id", "!=", self.company.currency_id.id)], limit=1
        )
        if not usd:
            self.skipTest("No hay moneda extranjera disponible")
        date = self._date(2)
        self._purchase_receipt(2, 10, date, currency=usd)
        _batch, line = self._calculate()
        expected = usd._convert(10, self.company.currency_id, self.company, date.date(), round=False)
        self.assertAlmostEqual(line.purchase_1_price, expected)

    def test_10_company_isolation(self):
        other = self.env["res.company"].create({"name": "Otra compañía"})
        candidates = self.env["indoor.standard.cost.batch"].create(
            {"company_id": self.company.id, "closing_date": self.closing_date}
        )._prepare_purchase_candidates(self.product, fields.Datetime.to_string(datetime.combine(self.closing_date, time.max)))
        self.assertNotIn(other.id, [item["line"].company_id.id for values in candidates.values() for item in values])

    def test_11_avco_product_is_not_applied(self):
        self.category.property_cost_method = "average"
        batch, line = self._calculate()
        self.assertEqual(line.validation_status, "invalid_method")
        batch.action_approve()
        batch.action_apply()
        self.assertEqual(self.product.standard_price, 100.0)

    def test_12_batch_cannot_be_applied_twice(self):
        self._purchase_receipt(1, 120, self._date(2))
        batch, _line = self._calculate()
        batch.action_approve()
        batch.action_apply()
        with self.assertRaises(UserError):
            batch.action_apply()

    def test_13_standard_price_creates_native_svl(self):
        input_account, output_account, valuation_account, expense_account, journal = _create_accounting_data(self.env)
        self.product.property_account_expense_id = expense_account
        self.category.write({
            "property_valuation": "real_time",
            "property_stock_account_input_categ_id": input_account.id,
            "property_stock_account_output_categ_id": output_account.id,
            "property_stock_valuation_account_id": valuation_account.id,
            "property_stock_journal": journal.id,
        })
        self._purchase_receipt(2, 100, self._date(2))
        before = self.env["stock.valuation.layer"].search_count([("product_id", "=", self.product.id)])
        self.product.standard_price = 150
        after = self.env["stock.valuation.layer"].search_count([("product_id", "=", self.product.id)])
        self.assertGreater(after, before)
        revaluation = self.env["stock.valuation.layer"].search(
            [("product_id", "=", self.product.id), ("quantity", "=", 0)],
            order="id desc", limit=1,
        )
        self.assertTrue(revaluation.account_move_id)
        self.assertEqual(len(revaluation.account_move_id.line_ids), 2)

    def test_14_zero_stock_has_zero_revaluation(self):
        self._purchase_receipt(1, 120, self._date(2))
        self._stock_out(1)
        _batch, line = self._calculate()
        self.assertAlmostEqual(line.stock_qty, 0.0)
        self.assertAlmostEqual(line.revaluation_difference, 0.0)

    def _stock_out(self, qty):
        move = self.env["stock.move"].create(
            {
                "name": "Salida test", "product_id": self.product.id,
                "product_uom_qty": qty, "product_uom": self.product.uom_id.id,
                "location_id": self.stock_location.id, "location_dest_id": self.customer_location.id,
                "company_id": self.company.id,
            }
        )
        self._finish_move(move, qty)
        move.date = self._date(1)

    def test_15_negative_stock_blocks_application(self):
        self._stock_out(1)
        batch, line = self._calculate()
        self.assertEqual(line.validation_status, "negative_stock")
        batch.action_approve()
        with self.assertRaises(ValidationError):
            batch.action_apply()

    def test_16_supplier_return_reduces_received_quantity(self):
        _order, pol, receipt = self._purchase_receipt(10, 100, self._date(3))
        returned = self.env["stock.move"].create(
            {
                "name": "Devolución", "product_id": self.product.id,
                "product_uom_qty": 4, "product_uom": self.product.uom_id.id,
                "location_id": self.stock_location.id, "location_dest_id": self.supplier_location.id,
                "company_id": self.company.id, "purchase_line_id": pol.id,
                "origin_returned_move_id": receipt.id, "to_refund": True,
            }
        )
        self._finish_move(returned, 4)
        returned.date = self._date(2)
        _batch, line = self._calculate()
        self.assertEqual(line.purchase_1_qty, 6)

    def test_17_approved_override_preserves_both_values(self):
        self._purchase_receipt(1, 120, self._date(2))
        batch, line = self._calculate()
        line.approved_standard_price = 125
        batch.action_approve()
        self.assertEqual(line.calculated_standard_price, 120)
        self.assertEqual(line.approved_standard_price, 125)
        self.assertEqual(line.approved_changed_by, self.env.user)

    def test_18_explicit_bulk_opt_in(self):
        template = self.env["product.template"].create(
            {"name": "Producto elegible", "is_storable": True, "categ_id": self.category.id}
        )
        self.assertFalse(template.use_monthly_standard_cost)
        batch = self.env["indoor.standard.cost.batch"].create(
            {"company_id": self.company.id, "closing_date": self.closing_date}
        )
        batch.action_include_eligible_products()
        self.assertTrue(template.use_monthly_standard_cost)
