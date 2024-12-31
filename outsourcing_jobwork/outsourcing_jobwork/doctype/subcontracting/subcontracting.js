// Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
// For license information, please see license.txt
// frappe.ui.form.on('Subcontracting', {
    // refresh: function(frm) {

    // }
// });

frappe.ui.form.on("Subcontracting", {
    in_or_out: function (frm) {
        if (frm.doc.out_entry_type === 'Subcontracting') {
            frappe.call({
                method: 'update_warehouse',
                doc: frm.doc,
                callback: function (r) {
                    refresh_field(["source_warehouse","target_warehouse"])
                }
            });
        }
    }
});

frappe.ui.form.on("Subcontracting", {
    company: function (frm) {
        frappe.call({
            method: 'update_company_address',
            doc: frm.doc,
            callback: function (r) {
                refresh_field(["company_address","company_gstin"])
            }
        });
    }
});

frappe.ui.form.on("Subcontracting", {
    supplier_id: function (frm) {
        frappe.call({
            method: 'update_supplier_address',
            doc: frm.doc,
            callback: function (r) {
                refresh_field(["company_address","company_gstin"])
            }
        });
    }
});

// ================================================================================= Address ===============================================================================

frappe.ui.form.on('Subcontracting', {
    supplier_address: function(frm) {
        if (frm.doc.supplier_address) {
            frappe.call({
                method: "alpha_customization.alpha_customization.blanket_order_address.get_display_address_for_blanket_order",
                args: {
                    address_id: frm.doc.supplier_address
                },
                callback: function(r) {
                    if (r.message) {

                        frm.doc.sup_adderss = r.message; // Assign m to sup_adderss field
                        frm.refresh_field('sup_adderss'); // Refresh the field to update its value on the form
                    }
                }
            });
        }
    },
});



function method_call_method(frm, party, party_type) {
    frappe.call({
        method: "alpha_customization.alpha_customization.blanket_order_address.get_address_for_blanket_order",
        args: {
            party: party,
            party_type: party_type

        },
        callback: function(r) {
            if (r.message) {
                var k = r.message[0];
                var m = r.message[1];

                frm.doc.supplier_address = k; // Assign k to supplier_address field
                frm.doc.sup_adderss = r.message[1]; // Assign m to sup_adderss field
                frm.refresh_field('supplier_address'); // Refresh the field to update its value on the form
                frm.refresh_field('sup_adderss'); // Refresh the field to update its value on the form


            }
        }
    });
}


// frappe.ui.form.on('Subcontracting', {
//     supplier_id: function(frm) {
//         if (frm.doc.supplier_id) {

//             method_call_method(frm, frm.doc.supplier_id, 'Supplier');
//         }
//     },
// });


// ================================================================================== ALL ================================================================================== 
function set_available_qty(frm, table, qty_field, item_code, warehouse_field) {
    const args = {
        table: table,
        qty_field: qty_field,
        item_code: item_code,
        warehouse_field: warehouse_field,
    };

    frm.call({
        method: 'set_available_qty',
        args: args,
        doc: frm.doc,
    });
}

function set_table_data(frm, table, table_field, field_data, qty_field, item_code, warehouse_field) {
    const args = {
        table: table,
        table_field: table_field,
        field_data: field_data,
        qty_field: qty_field,
        item_code: item_code,
        warehouse_field: warehouse_field,
    };

    frm.call({
        method: 'set_table_data',
        args: args,
        doc: frm.doc,
    });
}

async function set_raw_order_data(frm) {
    frm.clear_table("in_raw_item_subcontracting");
    frm.refresh_field('in_raw_item_subcontracting');
    frm.clear_table("bifurcation_out_subcontracting");
    frm.refresh_field('bifurcation_out_subcontracting');

    var args = {
        table: 'in_finished_item_subcontracting',
    };

    await frm.call({
        method: 'set_raw_order_data',
        args: args,
        doc: frm.doc,
    });
}

async function append_rejected_items_reasons(frm) {
    frm.clear_table("in_rejected_items_reasons_subcontracting");
    frm.refresh_field('in_rejected_items_reasons_subcontracting');

    await frm.call({
        method: 'rejected_item',
        doc: frm.doc,
    });
}


// function set_raw_order_data(frm) {
//     frm.clear_table("in_raw_item_subcontracting");
//     frm.refresh_field('in_raw_item_subcontracting');
//     frm.clear_table("bifurcation_out_subcontracting");
//     frm.refresh_field('bifurcation_out_subcontracting');

//     var args = {
//         table: 'in_finished_item_subcontracting',
//     };

//     frm.call({
//         method: 'set_raw_order_data',
//         args: args,
//         doc: frm.doc,
//     })
// }

// function append_rejected_items_reasons(frm) {
//     frm.clear_table("in_rejected_items_reasons_subcontracting");
//     frm.refresh_field('in_rejected_items_reasons_subcontracting');

//     frm.call({
//         method: 'rejected_item',
//         doc: frm.doc,
//     })

// }


function bifurgation_quantity_calculate(frm) {
    frm.call({
        method: 'bifurgation_quantity_calculate',
        doc: frm.doc,
    })

}

function set_field_filter(frm) {
    const field_filter = [{
            field: "source_warehouse",
            filter: [
                ["Warehouse", "company", '=', frm.doc.company]
            ]
        },
        {
            field: "target_warehouse",
            filter: [
                ["Warehouse", "company", '=', frm.doc.company]
            ]
        },
        {
            field: "linking_option",
            filter: [
                ["DocType", "name", 'in', ["Blanket Order", "Purchase Order"]]
            ]
        },
        {
            field: "blanket_order",
            filter: [
                ["Blanket Order", "blanket_order_type", '=', 'Purchasing'],
                ["Blanket Order", "supplier", '=', frm.doc.supplier_id],
                ["Blanket Order", "company", '=', frm.doc.company],
                ["Blanket Order", "docstatus", '=', 1]
            ]
        },
        {
            field: "purchase_order",
            filter: [
                ["Purchase Order", "supplier", '=', frm.doc.supplier_id],
                ["Purchase Order", "company", '=', frm.doc.company],
                ["Purchase Order", "docstatus", '=', 1]
            ]
        },
        {
            field: "item_group",
            filter: [
                ["Item Group", "company", '=', frm.doc.company],
            ]
        },
    ];

    for (const i of field_filter) {
        frm.set_query(i.field, function() {
            return {
                filters: i.filter
            };
        });
    }
}

function set_table_filter(frm) {
    var company_field = 'custom_company'
    const child_table_field_filter = [{
            field: "source_warehouse",
            table: "items_subcontracting",
            filter: [
                ["Warehouse", "company", '=', frm.doc.company]
            ]
        },
        {
            field: "source_warehouse",
            table: "loan_items_subcontracting",
            filter: [
                ["Warehouse", "company", '=', frm.doc.company]
            ]
        },
        {
            field: "target_warehouse",
            table: "items_subcontracting",
            filter: [
                ["Warehouse", "company", '=', frm.doc.company]
            ]
        },
        {
            field: "target_warehouse",
            table: "loan_items_subcontracting",
            filter: [
                ["Warehouse", "company", '=', frm.doc.company]
            ]
        },
        {
            field: "raw_item_code",
            table: "items_subcontracting",
            filter: [
                ["Item", company_field, '=', frm.doc.company]
            ]
        },
        {
            field: "in_item_code",
            table: "in_finished_item_subcontracting",
            filter: [
                ["Item", company_field, '=', frm.doc.company]
            ]
        },
        {
            field: "order_type",
            table: "in_finished_item_subcontracting",
            filter: [
                ["DocType", 'name', 'in', ['Blanket Order', 'Purchase Order']]
            ]
        },
    ];

    for (const j of child_table_field_filter) {
        frm.set_query(j.field, j.table, function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return {
                filters: j.filter
            };
        });
    }

}


function set_out_sub_list(frm) {
    frm.clear_table("out_subcontracting_list");
    frm.refresh_field('out_subcontracting_list');
    frm.call({
        method: 'set_out_sub_list',
        doc: frm.doc,
    })

}

// ================================================================================== Subcontracting ================================================================================== 
frappe.ui.form.on('Subcontracting', {
    subcontracting_operations: function(frm) {
        frm.call({
            method: 'set_operation',
            doc: frm.doc,
        })

    },
});

frappe.ui.form.on("Subcontracting", {
    setup: function(frm) {
        set_field_filter(frm);
        set_table_filter(frm);
        frm.set_query("select_order", "in_finished_item_subcontracting", function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            if (d.order_type == "Blanket Order") {
                return {

                    filters: [
                        ["Blanket Order", "blanket_order_type", '=', 'Purchasing'],
                        ["Blanket Order", "supplier", '=', frm.doc.supplier_id], // Replace with your actual filter criteria
                        ["Blanket Order", "company", '=', frm.doc.company],
                        ["Blanket Order", "docstatus", '=', 1],
                    ]
                };
            }
            if (d.order_type == 'Purchase Order') {
                return {

                    filters: [
                        ["Purchase Order", "supplier", '=', frm.doc.supplier_id], // Replace with your actual filter criteria
                        ["Purchase Order", "company", '=', frm.doc.company],
                        ["Purchase Order", "docstatus", '=', 1],
                    ]
                };
            }

        });
    },

    company: function(frm) {
        set_field_filter(frm);
        set_table_filter(frm);
        set_out_sub_list(frm);

    },

    supplier_id: function(frm) {
        set_field_filter(frm);
        set_table_filter(frm);
        set_out_sub_list(frm);
        if (frm.doc.supplier_id) {

            method_call_method(frm, frm.doc.supplier_id, 'Supplier');
        }

    },

    in_or_out: function(frm) {

        set_out_sub_list(frm);

    },

	without_order: function(frm) {

        set_out_sub_list(frm);

    },

    source_warehouse: function(frm) {
        if (frm.doc.in_or_out == 'OUT') {
            if (frm.doc.out_entry_type == 'Material Loan Given') {
                set_table_data(frm, 'loan_items_subcontracting', 'source_warehouse', frm.doc.source_warehouse, 'available_quantity', 'finished_item_code', 'source_warehouse');
            } else {
                set_table_data(frm, 'items_subcontracting', 'source_warehouse', frm.doc.source_warehouse, 'available_quantity', 'raw_item_code', 'source_warehouse');
            }
        } else {
            if (frm.doc.in_entry_type == 'Material Loan Given') {
                set_table_data(frm, 'in_loan_items_subcontracting', 'source_warehouse', frm.doc.source_warehouse, 'available_quantity', 'finished_item_code', 'source_warehouse');
            } else {
                // set_table_data(frm, 'in_raw_item_subcontracting','source_warehouse',frm.doc.source_warehouse,'available_quantity','raw_item_code','source_warehouse');
                // set_table_data(frm, 'in_rejected_items_reasons_subcontracting','source_warehouse',frm.doc.source_warehouse,'available_quantity','raw_item_code','source_warehouse');
                frm.call({
                    method: 'set_source_warehouse',
                    doc: frm.doc,
                })
            }
        }

    },


    target_warehouse: function(frm) {
        if (frm.doc.in_or_out == 'OUT') {
            if (frm.doc.out_entry_type == 'Material Loan Given') {
                set_table_data(frm, 'loan_items_subcontracting', 'target_warehouse', frm.doc.target_warehouse);
            } else {
                set_table_data(frm, 'items_subcontracting', 'target_warehouse', frm.doc.target_warehouse);
            }
        } else {
            if (frm.doc.in_entry_type == 'Material Loan Given') {
                set_table_data(frm, 'in_loan_items_subcontracting', 'target_warehouse', frm.doc.target_warehouse);
            } else {
                set_table_data(frm, 'in_finished_item_subcontracting', 'target_warehouse', frm.doc.target_warehouse);
            }
        }
    },

    blanket_order: function(frm) {
        frm.clear_table("in_finished_item_subcontracting");
        frm.refresh_field('in_finished_item_subcontracting');
        frm.call({
            method: 'set_in_finished_item',
            doc: frm.doc,
        })
		set_out_sub_list(frm);
    },


    purchase_order: function(frm) {
        frm.clear_table("in_finished_item_subcontracting");
        frm.refresh_field('in_finished_item_subcontracting');
        frm.call({
            method: 'set_in_finished_item',
            doc: frm.doc,
        })
		set_out_sub_list(frm);
    },

});


frappe.ui.form.on('Subcontracting', {
    item_group: function(frm) {
        frm.set_query("raw_item_code", "items_subcontracting", function(doc, cdt, cdn) {
            let d = locals[cdt][cdn];
            return {
                filters: [
                    ['Item', 'custom_company', '=',frm.doc.company ],
                    ['Item', 'item_group', '=',frm.doc.item_group ],

                ]
            };
        });
    }
});	
	
// ================================================================================== Out Subcontracting List ================================================================================== 

frappe.ui.form.on('Out Subcontracting List', {
    check: function(frm) {
        frm.clear_table("in_finished_item_subcontracting");
        frm.refresh_field('in_finished_item_subcontracting');
        frm.call({
            method: 'set_out_list_in_finished_item',
            doc: frm.doc,
        })
    },
});

frappe.ui.form.on('Out Subcontracting List', {
    subcontracting_operations: function(frm) {
        frm.clear_table("in_finished_item_subcontracting");
        frm.refresh_field('in_finished_item_subcontracting');
        frm.call({
            method: 'set_out_list_in_finished_item',
            doc: frm.doc,
        })
    },
});
// ================================================================================== Items Subcontracting ================================================================================== 
frappe.ui.form.on('Items Subcontracting', {
    raw_item_code: function(frm) {
        // set_available_qty(frm, 'items_subcontracting','available_quantity','raw_item_code','source_warehouse');
        set_table_data(frm, 'items_subcontracting', 'source_warehouse', frm.doc.source_warehouse, 'available_quantity', 'raw_item_code', 'source_warehouse');

    },
    source_warehouse: function(frm) {
        set_available_qty(frm, 'items_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    }
});
frappe.ui.form.on('Items Subcontracting', {
    raw_item_code: function(frm) {
        frm.call({
            method: 'set_weight_item',
            doc: frm.doc,
        })

    },
});

frappe.ui.form.on('Items Subcontracting', {
    production_quantity: function(frm) {
        frm.call({
            method: 'set_weight_item',
            doc: frm.doc,
        })

    },
});


// ================================================================================== Loan Items Outsourcing Job Work ================================================================================== 

frappe.ui.form.on('Loan Items Outsourcing Job Work', {
    finished_item_code: function(frm) {
        set_available_qty(frm, 'loan_items_subcontracting', 'available_quantity', 'finished_item_code', 'source_warehouse');
    },
    source_warehouse: function(frm) {
        set_available_qty(frm, 'loan_items_subcontracting', 'available_quantity', 'finished_item_code', 'source_warehouse');
    }
});

// ================================================================================== IN Finished Item Subcontracting ================================================================================== 

frappe.ui.form.on('IN Finished Item Subcontracting', {
    in_item_code: function(frm) {
        set_raw_order_data(frm);
    },
    operation: function(frm) {
        set_raw_order_data(frm);
    },
    unvaried: function(frm) {
        set_raw_order_data(frm);
    },

    as_it_is: async function(frm) {
        await set_raw_order_data(frm);
        await append_rejected_items_reasons(frm);
    },
    cr_casting_rejection: async function(frm) {
        await set_raw_order_data(frm);
        await append_rejected_items_reasons(frm);
    },
    mr_machine_rejection: async function(frm) {
        await set_raw_order_data(frm);
        await append_rejected_items_reasons(frm);
    },
    rw_rework: async function(frm) {
        await set_raw_order_data(frm);
        await append_rejected_items_reasons(frm);
    },
    quantity: function(frm) {
        
		set_raw_order_data(frm);

    }
});


// ================================================================================== Bifurcation Out Subcontracting ================================================================================== 

frappe.ui.form.on('Bifurcation Out Subcontracting', {
    production_quantity: function(frm) {
        frm.call({
            method: 'validate_bifurcation_out_subcontracting',
            doc: frm.doc,
        })

    },
    ok_quantity: function(frm) {
        bifurgation_quantity_calculate(frm);
    },
    cr_quantity: function(frm) {
        bifurgation_quantity_calculate(frm);
    },
    mr_quantity: function(frm) {
        bifurgation_quantity_calculate(frm);
    },
    rw_quantity: function(frm) {
        bifurgation_quantity_calculate(frm);
    },
    as_it_is_quantity: function(frm) {
        bifurgation_quantity_calculate(frm);
    },

    raw_item_code: function(frm) {
        set_available_qty(frm, 'bifurcation_out_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    },
    source_warehouse: function(frm) {
        set_available_qty(frm, 'bifurcation_out_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    }
});

// ================================================================================== IN Rejected Items Reasons Subcontracting ================================================================================== 


frappe.ui.form.on('IN Rejected Items Reasons Subcontracting', {
    quantity: function(frm) {
        frm.call({
            method: 'update_get_rejections',
            doc: frm.doc,
        });

    },

    raw_item_code: function(frm) {
        set_available_qty(frm, 'in_rejected_items_reasons_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    },
    source_warehouse: function(frm) {
        set_available_qty(frm, 'in_rejected_items_reasons_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    }
});

// ================================================================================== IN Raw Item Subcontracting ================================================================================== 

frappe.ui.form.on('IN Raw Item Subcontracting', {
    raw_item_code: function(frm) {
        set_available_qty(frm, 'in_raw_item_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    },
    source_warehouse: function(frm) {
        set_available_qty(frm, 'in_raw_item_subcontracting', 'available_quantity', 'raw_item_code', 'source_warehouse');
    }
});

// ================================================================================== Loan Items Subcontracting ================================================================================== 

frappe.ui.form.on('Loan Items Subcontracting', {
    finished_item_code: function(frm) {
        // set_available_qty(frm, 'items_subcontracting','available_quantity','raw_item_code','source_warehouse');
        set_table_data(frm, 'loan_items_subcontracting', 'source_warehouse', frm.doc.source_warehouse, 'available_quantity', 'finished_item_code', 'source_warehouse');

    },
    source_warehouse: function(frm) {
        set_available_qty(frm, 'loan_items_subcontracting', 'available_quantity', 'finished_item_code', 'source_warehouse');
    }
});