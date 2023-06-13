# Copyright (c) 2023, malnozilye and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters as validate_trial_filters
from erpnext.accounts.report.trial_balance_for_party.trial_balance_for_party import toggle_debit_credit, is_party_name_visible
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)


def execute(filters=None):
	filters = frappe._dict(filters)
	validate_filters(filters)

	show_party = cstr(filters.group_by) != "Group by Project"
	show_party_type = not filters.party_type
	show_party_name = is_party_name_visible(filters)
	show_project_subject = has_project_subject(filters)

	columns = get_columns(filters, show_project_subject, show_party, show_party_type, show_party_name)
	data = get_data(filters, show_project_subject, show_party_name)

	# columns, result, message, chart, report_summary, skip_total_row
	return columns, data, None, None, None, not filters.group_by


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("{0} is mandatory").format(_("Company")))

	if not filters.get("account"):
		frappe.throw(_("{0} is mandatory").format(_("Account")))

	validate_trial_filters(filters)

	if filters.get("party"):
		filters.project = frappe.parse_json(filters.get("project"))

	if filters.get("cost_center"):
		filters.cost_center = frappe.parse_json(filters.get("cost_center"))

	if not filters.group_by:
		if isinstance(filters.project, str):
			filters.project = [filters.project]
		elif len(filters.project or []) != 1:
			frappe.throw(_("Choose One Project for detailed report"))

	elif filters.group_by == "Group by Party" and not filters.party_type:
		frappe.throw(_("Party Type is required, if grouped by party"))

	if filters.get("project"):
		filters.project = frappe.parse_json(filters.get("project"))


def get_data(filters, show_project_subject, show_party_name):
	projects = get_projects(filters, show_project_subject)

	parties = get_parties(filters, show_party_name)

	key_lambda = get_key_lambda(cstr(filters.group_by))
	opening_balances = get_opening_balances(filters, key_lambda)
	balances_within_period = get_balances_within_period(filters, key_lambda)

	currency = get_currency(filters)

	data = []

	for proj in projects:
		for party in parties:
			rows = prepare_row(proj, party, currency, opening_balances, balances_within_period, filters, key_lambda)
			data += rows

	return data


def get_projects(filters, show_project_subject):
	project_fields = ["name", "project_name"]
	if show_project_subject:
		project_fields.append("project_subject")

	project_filters = None

	if filters.get("project"):
		project_filters = {"name": ["in", filters.project]}

	projects = frappe.get_all(
		"Project",
		fields=project_fields,
		filters=project_filters,
		order_by="name",
	)
	return projects


def get_parties(filters, show_party_name):
	if filters.group_by == "Group by Party":
		party_filter = None
		party_fields = ["name"]
		if show_party_name:
			party_fields.append(f"{get_party_name_field(filters.party_type)} as party_name")

		if filters.party:
			party_filter = {"name": ["in", filters.party]}

		parties = frappe.get_all(
			filters.party_type,
			fields=party_fields,
			filters=party_filter,
			order_by="name",
		)
	else:
		parties = [frappe._dict()]

	return parties


def get_currency(filters):
	if filters.show_base_currency:
		currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	else:
		currency = frappe.get_cached_value("Account", filters.account, "account_currency")

	return currency


def prepare_row(project, party, currency, opening_balances, balances_within_period, filters, _get_key):
	row = {
		"project": project.name,
		"project_name": project.project_name,
		"project_subject": project.project_subject,
		"party": party.name,
		"party_name": party.party_name,
		"currency": currency,
	}
	opening_debit, opening_credit = opening_balances.get(_get_key(project.name, party.name), [0, 0])
	row.update({"opening_debit": opening_debit, "opening_credit": opening_credit})

	debit = credit = closing_debit = closing_credit = None

	# within period
	# grouping
	data = []
	if filters.group_by:
		debit, credit = balances_within_period.get(_get_key(project.name, party.name), [0, 0])
		row.update({"debit": debit, "credit": credit})
		# closing
		closing_debit, closing_credit = toggle_debit_credit(
			opening_debit + debit, opening_credit + credit
		)
		row.update({"closing_debit": closing_debit, "closing_credit": closing_credit})

		append_to_res(data, row, filters)
	# detailed
	else:
		inner_row = {**row}
		inner_row.update({
			"project": _("Opening"),
			"project_name": "",
			"debit": opening_debit,
			"credit": opening_credit,
			"closing_debit": opening_debit,
			"closing_credit": opening_credit
		})
		append_to_res(data, inner_row, filters)
		for i in balances_within_period:
			inner_row = {**row}
			opening_debit += flt(i.get("debit"))
			opening_credit += flt(i.get("credit"))

			closing_debit, closing_credit = toggle_debit_credit(
				opening_debit, opening_credit
			)
			if i.get("party_type"):
				party_name_field = get_party_name_field(i["party_type"])
				i["party_name"] = frappe.get_cached_value(i["party_type"], i["party"], party_name_field)

			inner_row.update(i)
			inner_row.update({"closing_debit": closing_debit, "closing_credit": closing_credit})
			append_to_res(data, inner_row, filters)

	return data


def append_to_res(res, row, filters):
	has_value = False
	if row.get("opening_debit") or row.get("opening_credit") or row.get("debit") or row.get("credit") or row.get("closing_debit") or row.get("closing_credit"):
		has_value = True

	if cint(filters.show_zero_values) or has_value:
		res.append(row)


def get_opening_balances(filters, _get_key):
	return _get_balance(filters, _get_key, None, {
			"posting_date": ["<", filters.get("from_date")],
			"ifnull(is_opening, 'No')": "Yes",
		},
		True,
		toggle_debit_credit,
	)


def get_balances_within_period(filters, _get_key):
	return _get_balance(filters, _get_key, {
			"posting_date": ["between", [filters.get("from_date"), filters.get("to_date")]],
			"ifnull(is_opening, 'No')": "No",
		},
		None,
		filters.group_by,
		(lambda d, c: (d, c)) if filters.group_by else None
	)


def _get_balance(filters, _get_key, gl_filters_update, gl_or_filters, grouping, manipulate_res):
	gl_filters = {
		"company": filters.get("company"),
		"account": filters.get("account"),
		"is_cancelled": 0,
		"posting_date": ["<=", filters.get("to_date")],
	}
	gl_filters.update(gl_filters_update or {})

	gl_filters = _update_filters(filters, gl_filters)

	if filters.show_base_currency:
		debit_field = "debit"
		credit_field = "credit"
	else:
		debit_field = "debit_in_account_currency"
		credit_field = "credit_in_account_currency"

	if grouping:
		debit_field = f"sum({debit_field})"
		credit_field = f"sum({credit_field})"
		group_by = "project"
		if filters.group_by == "Group by Party":
			group_by += ", party_type"
	else:
		group_by = None

	gle = frappe.get_all("GL Entry", fields=[
			"project",
			"posting_date",
			"party_type",
			"party",
			"voucher_type",
			"voucher_no",
			"posting_date",
			f"{debit_field} as debit",
			f"{credit_field} as credit",
		],
		filters=gl_filters,
		or_filters=gl_or_filters,
		group_by=group_by,
		order_by="posting_date, modified"
	)

	if manipulate_res:
		res = frappe._dict()
		for d in gle:
			debit, credit = manipulate_res(d.debit, d.credit)
			res.setdefault(_get_key(d.project,  d.party), [debit, credit])
		return res
	else:
		return gle


def _update_filters(filters, gl_filters):
	if filters.project:
		gl_filters["project"] = ["in", filters.project]

	if filters.group_by != "Group by Project":
		if filters.party_type:
			gl_filters["party_type"] = filters.party_type
		if filters.party:
			gl_filters["party"] = ["in", filters.party]

	cost_center_dim = frappe._dict({"fieldname": "cost_center", "document_type": "Cost Center"})

	accounting_dimensions = get_accounting_dimensions(as_list=False) + [cost_center_dim]

	for dimension in accounting_dimensions:
		if filters.get(dimension.fieldname):
			if frappe.get_cached_value("DocType", dimension.document_type, "is_tree"):
				filters[dimension.fieldname] = get_dimension_with_children(
					dimension.document_type, filters.get(dimension.fieldname)
				)

			gl_filters[dimension.fieldname] = ["in", filters[dimension.fieldname]]

	return gl_filters


def get_columns(filters, show_project_subject, show_party, show_party_type, show_party_name):
	columns = [
		{
			"fieldname": "project",
			"label": _("Project"),
			"fieldtype": "Link",
			"options": "Project",
			"width": 200,
		},
		{
			"fieldname": "project_name",
			"label": _("Project Name"),
			"fieldtype": "Data",
			"width": 200,
			"hidden": True,
		},
	]
	if show_project_subject:
		columns.append({
			"fieldname": "project_subject",
			"label": _("Project Subject"),
			"fieldtype": "Data",
			"width": 150,
		})

	if show_party:
		if show_party_type:
			columns += [
				{
					"fieldname": "party_type",
					"label": _("Party Type"),
					"fieldtype": "Data",
					"width": 120,
				},
				{
					"fieldname": "party",
					"label": _("Party"),
					"fieldtype": "Dynamic Link",
					"options": "party_type",
					"width": 150,
				},
			]
		else:
			columns.append({
				"fieldname": "party",
				"label": _(filters.party_type),
				"fieldtype": "Link",
				"options": filters.party_type,
				"width": 150,
			})

		if show_party_name:
			columns.append({
				"fieldname": "party_name",
				"label": _((filters.party_type or "Party") + " Name"),
				"fieldtype": "Data",
				"width": 150,
			})

	if filters.group_by:
		columns += [
			{
				"fieldname": "opening_debit",
				"label": _("Opening (Dr)"),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
			{
				"fieldname": "opening_credit",
				"label": _("Opening (Cr)"),
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120,
			},
		]
	else:
		columns.insert(0, {
				"fieldname": "posting_date",
				"label": _("Posting Date"),
				"fieldtype": "Date",
				"width": 120,
			})

	columns += [
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "closing_debit",
			"label": _("Closing (Dr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "closing_credit",
			"label": _("Closing (Cr)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]

	if not filters.group_by:
		columns += [
			{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 120},
			{
				"label": _("Voucher No"),
				"fieldname": "voucher_no",
				"fieldtype": "Dynamic Link",
				"options": "voucher_type",
				"width": 180,
			},
		]

	return columns


def has_project_subject(filters):
	project_meta = frappe.get_meta("Project")
	return project_meta.has_field("project_subject")


def get_party_name_field(party_type):
	if party_type in ("Customer", "Supplier", "Employee", "Member"):
		party_name_field = "{0}_name".format(frappe.scrub(party_type))
	elif party_type == "Student":
		party_name_field = "first_name"
	elif party_type == "Shareholder":
		party_name_field = "title"
	else:
		party_name_field = "name"

	return party_name_field


def get_key_lambda(group_by):
	if group_by == "Group by Party":
		return lambda project, party: (project, party)
	else:
		return lambda project, party=None: project
