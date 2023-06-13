// Copyright (c) 2023, malnozilye and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Project Balance"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
			"on_change": function(query_report) {
				var company = query_report.get_values().company;
				get_default_account(company).then(function(account){
					frappe.query_report.set_filter_value({
						account: account,
					});
				});
			}
		},
		{
			"fieldname": "account",
			"label": __("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function(){
				return {
					filters: {
						is_group: 0,
					}
				};
			},
			"reqd": 1
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": frappe.defaults.get_user_default("fiscal_year"),
			"reqd": 1,
			"on_change": function(query_report) {
				var fiscal_year = query_report.get_values().fiscal_year;
				if (!fiscal_year) {
					return;
				}
				frappe.model.with_doc("Fiscal Year", fiscal_year, function(r) {
					var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
					frappe.query_report.set_filter_value({
						from_date: fy.year_start_date,
						to_date: fy.year_end_date
					});
				});
			}
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type",
			"default": "Employee",
			"depends_on": "eval: doc.group_by != 'Group by Project'",
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "MultiSelectList",
			"depends_on": "eval: doc.group_by != 'Group by Project'",
			"get_data": function(txt) {
				var party_type = frappe.query_report.get_filter_value('party_type');
				var party = frappe.query_report.get_filter_value('party');
				if(!party_type) {
					frappe.throw(__("Please select Party Type first"));
				}
				return frappe.db.get_link_options(party_type, txt);
			}
		},
		{
			"fieldname":"project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			fieldtype: "Break",
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Cost Center', txt, {
					company: frappe.query_report.get_filter_value("company")
				});
			}
		},
		{
			"fieldname":"group_by",
			"label": __("Group by"),
			"fieldtype": "Select",
			"options": [
				"",
				{
					label: __("Group by Project"),
					value: "Group by Project",
				},
				{
					label: __("Group by Party"),
					value: "Group by Party",
				},
			],
			"default": "Group by Project"
		},
		{
			"fieldname": "show_zero_values",
			"label": __("Show zero values"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "show_base_currency",
			"label": __("Show in company currency"),
			"fieldtype": "Check"
		}
	],
};

erpnext.utils.add_dimensions('Project Balance', 9);

let setup_filters = frappe.query_report.setup_filters;

frappe.query_report.setup_filters = function(){
	setup_filters.apply(this, arguments);
	 this.filters.forEach(f => {
		 if (f.df && f.df.on_change){
			 f.df.on_change(this);
		 }
	 });
}

async function get_default_account(company){
	if (!company) {
		return;
	}

	let res = await frappe.db.get_value("Company", company, "default_employee_advance_account");
	if (res && res.message){
		return res.message.default_employee_advance_account;
	}
}
