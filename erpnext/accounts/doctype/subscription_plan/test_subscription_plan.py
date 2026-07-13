# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestSubscriptionPlan(ERPNextTestSuite):
	"""Subscription Plan validates its interval and computes a rate. The Monthly
	Rate branch multiplies cost by the number of months in the billing window."""

	def setUp(self):
		frappe.set_user("Administrator")

	def make_plan(self, **args):
		args = frappe._dict(args)
		plan = frappe.new_doc("Subscription Plan")
		plan.plan_name = f"_Test Plan {frappe.generate_hash(length=6)}"
		plan.item = args.item or "_Test Item"
		plan.currency = args.currency or "INR"
		plan.price_determination = args.price_determination
		plan.cost = args.cost or 0
		plan.billing_interval = args.billing_interval or "Month"
		plan.billing_interval_count = (
			args.billing_interval_count if args.billing_interval_count is not None else 1
		)
		return plan

	def test_billing_interval_count_must_be_positive(self):
		plan = self.make_plan(price_determination="Fixed Rate", cost=100, billing_interval_count=0)
		self.assertRaises(frappe.ValidationError, plan.insert)

	def test_fixed_rate_applies_prorate_factor(self):
		plan = self.make_plan(price_determination="Fixed Rate", cost=100)
		plan.insert()
		self.assertEqual(get_plan_rate(plan.name), 100)
		self.assertEqual(get_plan_rate(plan.name, prorate_factor=0.5), 50)

	def test_price_list_rate_uses_billing_period_start(self):
		item = make_item(properties={"is_stock_item": 0})
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": f"_Test Subscription Prices {frappe.generate_hash(length=6)}",
				"currency": "INR",
				"selling": 1,
			}
		).insert()

		for price in (
			{"price_list_rate": 190, "valid_upto": "2026-12-31"},
			{"price_list_rate": 195, "valid_from": "2027-01-01"},
		):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item.name,
					"price_list": price_list.name,
					**price,
				}
			).insert()

		plan = self.make_plan(item=item.name, price_determination="Based On Price List")
		plan.price_list = price_list.name
		plan.insert()

		self.assertEqual(
			(
				get_plan_rate(plan.name, start_date="2026-12-31", end_date="2026-12-31"),
				get_plan_rate(plan.name, start_date="2027-01-01", end_date="2027-01-01"),
			),
			(190, 195),
		)

	def test_monthly_rate_within_year(self):
		plan = self.make_plan(price_determination="Monthly Rate", cost=100)
		plan.insert()
		# Jan 1 - Mar 31 is 3 whole months; month-aligned so proration is 0
		rate = get_plan_rate(plan.name, start_date="2026-01-01", end_date="2026-03-31")
		self.assertEqual(rate, 300)

	def test_monthly_rate_across_year_boundary(self):
		# a 14-month span (Jan 2026 to Feb 2027) bills all 14 months, not just the
		# 2-month remainder that relativedelta.months alone would give
		plan = self.make_plan(price_determination="Monthly Rate", cost=100)
		plan.insert()
		rate = get_plan_rate(plan.name, start_date="2026-01-01", end_date="2027-02-28")
		self.assertEqual(rate, 1400)
