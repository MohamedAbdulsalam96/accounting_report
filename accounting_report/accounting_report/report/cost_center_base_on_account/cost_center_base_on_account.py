# Copyright (c) 2022, Mohammed Alnozili and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.accounts.utils import get_balance_on

def execute(filters=None):
	# columns=[], data=[]
	cost_center = get_cost_centers(filters)
	accounts = get_accounts(filters)
	columns = get_columns(filters, cost_center, accounts)
	data = get_data(filters, cost_center, accounts)
	# data = []
	
	return columns, data
    

def get_columns(filters, cost_center, accounts):
	columns = []
	columns.append({
            "label": _("Cost Center"),
            "fieldtype": "Link",
			"options":"Cost Center",
            "fieldname": "cost_center",
            "width": 300
        })
	# columns.append({
	# 	"label": _(filters.budget),
    #         "fieldtype": "int",
    #         "fieldname": filters.budget,
    #         "width": 200
	# })
	if accounts:
		for a in accounts:
			columns.append({
				"label": _(a.name +" "+ a.account_currency),
				"fieldtype": "Currency",
				# "options":"Account",
				"fieldname": a.name,
				"width": 200
			})
	return columns


# def get_conditions(filters):
#     conditions = {}
#     if filters.log_frame_for and filters.document:
#         conditions["log_frame_for"] = filters.log_frame_for
#         conditions["document"] = filters.document
#     return conditions

def get_data(filters, cost_center, accounts):
	data = []
	print("get_data")
	print("cost_center"), cost_center
	count = 0
	if cost_center:
		for c in cost_center:
			data.append({"cost_center": c.name})
			for a in accounts:
				data[count].update({a.name: get_amount(a.name, c.name, filters.company)})
			count = count + 1

	
	return data

def get_cost_centers(filters):
	conditions = {}
	conditions["is_group"] = 0
	conditions["company"] = filters.company
	
	if filters.cost_center:
		conditions["parent_cost_center"] = filters.cost_center

	cost_center = frappe.get_list("Cost Center", filters = conditions,  fields=["name"])
	
	return cost_center
		
def get_accounts(filters):
	return frappe.get_list("Account", filters={"root_type": filters.root_type, 
	"is_group": 0, "report_type":"Profit and Loss", "company":filters.company},
	  fields=["name","account_currency"])



def get_amount(account, cost_center, company):
	balance = get_balance_on(
		account = account,
		company = company,
		cost_center = cost_center
	)
	return balance
	# return frappe.db.get_value('Budget Account', {"account": account, "parent": budget}, ['budget_amount'])
