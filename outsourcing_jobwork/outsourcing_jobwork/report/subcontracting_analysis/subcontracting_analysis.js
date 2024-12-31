// Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Subcontracting Analysis"] = {
	"filters": [
		{
            "fieldname": "company",
            "fieldtype": "Link",
            "label": "Company",
            "options": "Company",
			"reqd": 1
        },
        {
            "fieldname": "from_date",
            "fieldtype": "Date",
            "label": "From Date",
			"reqd": 1
        },
        {
            "fieldname": "to_date",
            "fieldtype": "Date",
            "label": "To Date",
			"reqd": 1
        },
        {
            "fieldname": "group_by",
            "fieldtype": "Select",
            "label": "Group By",
            "options": ["Group By Item", "Group By Supplier"],
            default: "Group By Item"
        },
		{
			fieldname: "supplier_id",
			label: __("Supplier Id"),
			fieldtype: "MultiSelectList",
			options: "Supplier",
			get_data: function(txt) {
				return frappe.db.get_link_options("Supplier", txt);
			},
			reqd: 0,
		},		{
			fieldname: "item",
			label: __("Item Id"),
			fieldtype: "MultiSelectList",
			options: "Item",
			get_data: function(txt) {
				return frappe.db.get_link_options("Item", txt);
			},
			reqd: 0,
		},
        // {
        //     "fieldname": "supplier_id",
        //     "fieldtype": "Link",
        //     "label": "Supplier Id",
        //     "options": "Supplier"
        // },
        // {
        //     "fieldname": "item",
        //     "fieldtype": "Link",
        //     "label": "Item Id",
        //     "options": "Item"
        // },
        {
            "fieldname": "include_weight",
            "fieldtype": "Check",
            "label": "Include Weight",
        },
	]
};


// // Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
// // For license information, please see license.txt
// /* eslint-disable */

// frappe.query_reports["Subcontracting Analysis"] = {
// 	"filters": [
// 		{
//             "fieldname": "company",
//             "fieldtype": "Link",
//             "label": "Company",
//             "options": "Company",
// 			"reqd": 1
//         },
//         {
//             "fieldname": "from_date",
//             "fieldtype": "Date",
//             "label": "From Date",
// 			"reqd": 1
//         },
//         {
//             "fieldname": "to_date",
//             "fieldtype": "Date",
//             "label": "To Date",
// 			"reqd": 1
//         },
//         {
//             "fieldname": "group_by",
//             "fieldtype": "Select",
//             "label": "Group By",
//             "options": ["Group By Item", "Group By Supplier"],
//             default: "Group By Item"
//         },
//         {
//             "fieldname": "supplier_id",
//             "fieldtype": "Link",
//             "label": "Supplier Id",
//             "options": "Supplier"
//         },
//         {
//             "fieldname": "item",
//             "fieldtype": "Link",
//             "label": "Item Id",
//             "options": "Item"
//         },
//         {
//             "fieldname": "include_weight",
//             "fieldtype": "Check",
//             "label": "Include Weight",
//         },
// 	]
// };
