
// Copyright (c) 2022, Mohammed Alnozili and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Account Base on  Cost Center"] = {
	"filters": [
		{
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "cost_center",
			fieldtype: "Link",
			options: "Cost Center",
			label: __("Cost Center"),
			get_query: function() {
				var company = frappe.query_report.get_filter_value('company');
			  return {
				filters: {
				  "is_group": 1,
				  "company": company

				}
			  };
			}
		  },
		  {
			fieldname: "root_type",
			fieldtype: "Select",
			options: "Expense\nIncome",
			default:"Expense",
			label: __("Root Type"),
			get_query: function() {
				var company = frappe.query_report.get_filter_value('company');
			  return {
				filters: {
				  "is_group": 0,
				  "company": company

				}
			  };
			}
		  },
		  {
			fieldname: "account",
			fieldtype: "Link",
			options: "Account",
			label: __("Account"),
			get_query: function() {
				var company = frappe.query_report.get_filter_value('company');
				var root_type = frappe.query_report.get_filter_value('root_type');
			  return {
				filters: {
				  "is_group": 1,
				  "company": company,
				  "root_type": root_type

				}
			  };
			}
		  },
	]
};
