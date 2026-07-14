# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Shared accounting boundary for PI valuation charges linked to Purchase Receipts."""

import frappe
from frappe.utils import flt


def get_active_pr_gl_accounts(purchase_receipts, accounts) -> dict[str, set[str]]:
	purchase_receipts = {name for name in purchase_receipts if name}
	accounts = {account for account in accounts if account}
	if not purchase_receipts or not accounts:
		return {}

	rows = frappe.get_all(
		"GL Entry",
		filters={
			"voucher_type": "Purchase Receipt",
			"voucher_no": ("in", purchase_receipts),
			"account": ("in", accounts),
			"is_cancelled": 0,
		},
		fields=["voucher_no", "account"],
	)

	accounts_by_purchase_receipt = {}
	for row in rows:
		accounts_by_purchase_receipt.setdefault(row.voucher_no, set()).add(row.account)

	return accounts_by_purchase_receipt


def get_srbnb_reclassified_valuation_tax(
	item_tax_amount,
	*,
	auto_accounting_for_stock,
	is_opening,
	is_stock_item,
	purchase_receipt,
	valuation_tax_accounts,
	active_pr_gl_accounts,
) -> float:
	"""Return the signed PI item tax only when its GL entry is reclassified to SRBNB."""
	valuation_tax_accounts = set(valuation_tax_accounts)
	if (
		auto_accounting_for_stock
		and is_opening == "No"
		and is_stock_item
		and purchase_receipt
		and flt(item_tax_amount)
		and valuation_tax_accounts
		and valuation_tax_accounts.isdisjoint(active_pr_gl_accounts)
	):
		return flt(item_tax_amount)

	return 0.0
