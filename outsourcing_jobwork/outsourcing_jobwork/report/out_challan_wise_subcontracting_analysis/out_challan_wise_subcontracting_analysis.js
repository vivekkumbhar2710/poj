// Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Out Challan Wise Subcontracting Analysis"] = {
	"filters": [
		{"fieldname": "company", "fieldtype": "Link", "label": "Company", "options": "Company", "reqd": 1},
        {"fieldname": "from_date", "fieldtype": "Date", "label": "From Date (OUT Challan)", "reqd": 1},
        {"fieldname": "to_date", "fieldtype": "Date", "label": "To Date (IN Challan)", "reqd": 1},
        {"fieldname": "out_challan_no", "fieldtype": "Link", "label": "Out Challan", "options": "Subcontracting"},
        {"fieldname": "out_item", "fieldtype": "Link", "label": "Out Item", "options": "Item"},
		{"fieldname": "supplier", "fieldtype": "Link", "label": "Supplier", "options": "Supplier"}
	]
};

