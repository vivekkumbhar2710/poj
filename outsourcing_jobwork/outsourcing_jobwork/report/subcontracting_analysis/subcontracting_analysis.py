# Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime

def execute(filters=None):
    columns, data = [], {}
    columns = get_col(filters)
    data = get_data(filters)
    return columns, data

def get_col(filters):
    columns = [
        {
            "fieldname": "supplier_name","fieldtype": "Data","label": "Supplier Name"
        },
        {
            "fieldname": "opening_qty","fieldtype": "Data","label": "Opening QTY",
        },
        {
            "fieldname": "production_out_quantity","fieldtype": "Data","label": "Dispatch QTY"
        },
        {
            "fieldname": "total_despatch_qty","fieldtype": "Data","label": "Total Dispatch QTY",
        },
        {
            "fieldname": "ok_quantity","fieldtype": "Float","label": "Ok QTY"
        },
        {
            "fieldname": "cr_quantity","fieldtype": "Float","label": "CR QTY"
        },
        {
            "fieldname": "mr_quantity","fieldtype": "Float","label": "MR QTY"
        },
        {
            "fieldname": "as_it_is_quantity","fieldtype": "Float","label": "AS IT IS QTY"
        },
        {
            "fieldname": "rw_quantity","fieldtype": "Float","label": "RW QTY"
        },
        {
            "fieldname": "prod_quantity","fieldtype": "Float","label": "Total Receipts"
        },
        {
            "fieldname": "production_remaining_quantity","fieldtype": "Float","label": "Balance"
        }
    ]

    if filters.get("group_by") == "Group By Item":
        columns.insert(0, {"fieldname": "raw_item_code","fieldtype": "Data","label": "Raw Item Code"})
        columns.insert(1,{"fieldname": "raw_item_name","fieldtype": "Data","label": "Raw Item Name"})
    else:
        columns.insert(1, {"fieldname": "raw_item_code","fieldtype": "Data","label": "Raw Item Code"})
        columns.insert(2,{"fieldname": "raw_item_name","fieldtype": "Data","label": "Raw Item Name"})

    if filters.get("include_weight") == 1:
        columns.append({"fieldname": "weight_per_unit","fieldtype": "Float","label": "Wt/Pc"})
        columns.append({"fieldname": "total_weight","fieldtype": "Float","label": "Total Receipts Weight"})
        columns.append({"fieldname": "total_balance_weight","fieldtype": "Float","label": "Total Balance Weight"})

    return columns

def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    sup_id = filters.get("supplier_id")
    comp = filters.get("company")
    item = filters.get("item")
    group_by = filters.get("group_by")

    sql_query = """
            SELECT 
                Date, 
                warehouse, 
                supplier_name,
                supplier_id,
                raw_item_code, 
                raw_item_name, 
                SUM(ok_quantity) AS ok_quantity, 
                SUM(cr_quantity) AS cr_quantity, 
                SUM(mr_quantity) AS mr_quantity, 
                SUM(as_it_is_quantity) AS as_it_is_quantity, 
                SUM(rw_quantity) AS rw_quantity, 
                SUM(prod_quantity) AS prod_quantity, 
                SUM(production_out_quantity) AS production_out_quantity, 
                weight_per_unit, 
                0 AS production_remaining_quantity
            FROM (
                SELECT 
                    sc.posting_date AS Date, 
                    sc.source_warehouse AS warehouse, 
                    sc.supplier_name, sc.supplier_id,
                    bos.raw_item_code, 
                    bos.raw_item_name, 
                    bos.ok_quantity, 
                    bos.cr_quantity, 
                    bos.mr_quantity, 
                    bos.as_it_is_quantity, 
                    bos.rw_quantity, 
                    (bos.ok_quantity + bos.cr_quantity + bos.mr_quantity + bos.as_it_is_quantity + bos.rw_quantity) AS prod_quantity, 
                    0 AS production_out_quantity, 
                    bos.weight_per_unit, 
                    0 AS production_remaining_quantity
                FROM 
                    `tabBifurcation Out Subcontracting` AS bos
                INNER JOIN 
                    `tabSubcontracting` sc ON sc.name = bos.parent
                WHERE 
                    sc.in_or_out = 'IN' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}

                UNION ALL

                SELECT 
                    sc.posting_date AS Date, 
                    sc.target_warehouse AS warehouse, 
                    sc.supplier_name, sc.supplier_id,
                    bos.raw_item_code, 
                    bos.raw_item_name, 
                    0 AS ok_quantity, 
                    0 AS cr_quantity, 
                    0 AS mr_quantity, 
                    0 AS as_it_is_quantity, 
                    0 AS rw_quantity, 
                    0 AS prod_quantity, 
                    bos.production_quantity AS production_out_quantity, 
                    bos.weight_per_unit, 
                    0 AS production_remaining_quantity
                FROM
                    `tabSubcontracting` AS sc
                INNER JOIN 
                    `tabItems Subcontracting` bos ON sc.name = bos.parent
                WHERE 
                    sc.in_or_out = 'OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
            ) AS combined_results
            GROUP BY  
                supplier_name, 
                raw_item_code
            """


    conditions = []
    params = [comp, from_date, to_date]

    if item:
        conditions.append("bos.raw_item_code in %s")
        params.append(item)

    if sup_id:
        conditions.append("sc.supplier_id in %s")
        params.append(sup_id)

    params = param(params, comp, from_date, to_date)

    if item:
        params.append(item)

    if sup_id:
        params.append(sup_id)

    cond = " AND " + " AND ".join(conditions) if conditions else ""
    sql_query = sql_query.format(condition = cond)

    data = frappe.db.sql(sql_query, tuple(params), as_dict=True)
    frappe.msgprint(str(data))
    for entry in data:
        warehouse = frappe.get_value("Supplier", {'name': entry['supplier_id']}, 'custom_subcontracting_warehouse')
        if warehouse:
            entry['opening_qty'] = get_all_available_quantity(entry['raw_item_code'], warehouse, filters)
        else:
            entry['opening_qty'] = 0.0
        entry['total_despatch_qty'] = entry['opening_qty'] + entry['production_out_quantity']
        entry['total_weight'] = entry['weight_per_unit'] * entry['prod_quantity']
        entry['total_balance_weight'] = entry['weight_per_unit'] * entry['total_despatch_qty']
        entry['production_remaining_quantity'] = entry['total_despatch_qty'] - entry['prod_quantity']


    if group_by == "Group By Supplier":
        sorted_data = sorted(data, key=lambda x: x['supplier_name'])
        subtotal = {
            'supplier_name': None,
            'raw_item_code': 'Subtotal',
            'raw_item_name': None,
            'opening_qty': 0.0,
            'total_despatch_qty': 0,
            'ok_quantity': 0.0,
            'cr_quantity': 0.0,
            'mr_quantity': 0.0,
            'as_it_is_quantity': 0.0,
            'rw_quantity': 0.0,
            'prod_quantity': 0.0,
            'production_out_quantity': 0.0,
            'production_remaining_quantity': 0.0,
            'weight_per_unit': 0.0,
            'total_weight': 0.0,
            'total_balance_weight': 0.0
        }
        result = []
        current_supplier = None
        for entry in sorted_data:
            if entry['supplier_name'] != current_supplier:
                if current_supplier is not None:
                    result.append(subtotal.copy())
                    subtotal = subtotal.fromkeys(subtotal, 0.0)
                    subtotal['raw_item_code'] = 'Subtotal'
                current_supplier = entry['supplier_name']
                subtotal['supplier_name'] = None
            for key in subtotal.keys():
                if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
                    subtotal[key] += entry[key]
            result.append(entry)
        result.append(subtotal)

    if group_by == "Group By Item":
        sorted_data = sorted(data, key=lambda x: x['supplier_name'])
        sorted_data = sorted(sorted_data, key=lambda x: x['raw_item_code'])
        subtotal = {
            'supplier_name': None,
            'raw_item_code': 'Subtotal',
            'raw_item_name': None,
            'opening_qty': 0.0,
            'total_despatch_qty': 0,
            'ok_quantity': 0.0,
            'cr_quantity': 0.0,
            'mr_quantity': 0.0,
            'as_it_is_quantity': 0.0,
            'rw_quantity': 0.0,
            'prod_quantity': 0.0,
            'production_out_quantity': 0.0,
            'production_remaining_quantity': 0.0,
            'weight_per_unit': 0.0,
            'total_weight': 0.0,
            'total_balance_weight': 0.0
        }
        result = []
        current_item_code = None
        for entry in sorted_data:
            if entry['raw_item_code'] != current_item_code:
                if current_item_code is not None:
                    subtotal['supplier_name'] = 'Subtotal'
                    result.append(subtotal.copy())
                    subtotal = subtotal.fromkeys(subtotal, 0.0)
                    subtotal['supplier_name'] = 'Subtotal'
                current_item_code = entry['raw_item_code']
                subtotal['raw_item_code'] = None
            for key in subtotal.keys():
                if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
                    subtotal[key] += entry[key]
            result.append(entry)
        result.append(subtotal)
    return result

def param(params, comp, from_date, to_date):
    params.append(comp)
    params.append(from_date)
    params.append(to_date)
    return params

def get_all_available_quantity(item_code, warehouse, filters): 
    from_date, to_date = filters.get('from_date'), filters.get('to_date')
    company_name = filters.get('company')

    opn_sum = 0
    opening_balance = frappe.db.sql("""
            SELECT qty_after_transaction 
            FROM `tabStock Ledger Entry` 
            WHERE posting_date < '{0}' 
                AND warehouse = '{1}' 
                AND item_code = '{2}' 
                AND company = '{3}' 
                AND is_cancelled='{4}'
            ORDER BY creation DESC 
            LIMIT 1
            """.format(from_date, warehouse, item_code, company_name, False), as_dict=True)
    if opening_balance:
        opn_sum = opening_balance[0].qty_after_transaction
    return opn_sum




# sql_query = """
#     SELECT Date, warehouse, supplier_name, raw_item_code, raw_item_name, SUM(ok_quantity) AS ok_quantity, SUM(cr_quantity) AS cr_quantity, SUM(mr_quantity) AS mr_quantity, SUM(as_it_is_quantity) AS as_it_is_quantity, SUM(rw_quantity) AS rw_quantity, SUM(production_quantity) AS production_quantity, SUM(production_out_quantity) AS production_out_quantity, weight_per_unit, 0 AS production_remaining_quantity
# FROM (
#     SELECT sc.posting_date AS Date, sc.source_warehouse as warehouse, sc.supplier_name, bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity, bos.as_it_is_quantity, bos.rw_quantity, (bos.ok_quantity+bos.cr_quantity+bos.mr_quantity+bos.as_it_is_quantity+bos.rw_quantity) as production_quantity, bos.production_out_quantity, bos.weight_per_unit,production_remaining_quantity
#     FROM 
#         `tabBifurcation Out Subcontracting` AS bos
#     INNER JOIN 
#         `tabSubcontracting` sc ON sc.name = bos.parent
#     WHERE 
#         sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
        
#     UNION ALL

#     SELECT sc.posting_date AS Date, sc.target_warehouse as warehouse, sc.supplier_name, bos.raw_item_code, bos.raw_item_name, 0 AS ok_quantity, 0 AS cr_quantity, 0 AS mr_quantity,0 AS as_it_is_quantity, 0 AS rw_quantity, 0 AS production_quantity, bos.production_quantity AS production_out_quantity, bos.weight_per_unit,0 AS production_remaining_quantity
#     FROM 
#         `tabSubcontracting` AS sc
#     INNER JOIN 
#         `tabItems Subcontracting` bos ON sc.name = bos.parent
#     WHERE sc.in_or_out = 'OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
# ) AS combined_results
# GROUP BY  
#     warehouse,
#     supplier_name, 
#     raw_item_code, 
#     raw_item_name, 
#     weight_per_unit;
#     """











# def get_data(filters):
#     from_date = filters.get("from_date")
#     to_date = filters.get("to_date")
#     sup_id = filters.get("supplier_id")
#     comp = filters.get("company")
#     item = filters.get("item")
#     group_by = filters.get("group_by")

#     sql_query = """
#                 SELECT sc.supplier_name, bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity, bos.rw_quantity, bos.production_quantity, bos.production_out_quantity,
#                 (bos.production_out_quantity - bos.production_quantity) as production_remaining_quantity
#                 FROM `tabBifurcation Out Subcontracting` as bos
#                 LEFT JOIN `tabSubcontracting` sc on sc.name = bos.parent
#                 WHERE sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1
#                 """
#     result = get_all_available_quantity(bos.raw_item_code, filters)
#     frappe.throw(str(result))
    
#     conditions = []
#     params = [comp, from_date, to_date]

#     if item:
#         conditions.append("bos.raw_item_code = %s")
#         params.append(item)

#     if sup_id:
#         conditions.append("sc.supplier_id = %s")
#         params.append(sup_id)

#     sql_query += " AND " + " AND ".join(conditions) if conditions else ""
#     data = frappe.db.sql(sql_query, tuple(params), as_dict=True)
#     # frappe.throw(str(data))

# posting_date = frappe.get_value("Subcontracting",{'name': entry['subcontracting'], 'in_or_out':'OUT'},'posting_date')
# from_d, to_d, post_d = datetime.strptime(from_date, "%Y-%m-%d"), datetime.strptime(to_date, "%Y-%m-%d"), datetime.strptime(str(posting_date), "%Y-%m-%d")
# if from_d <= post_d <= to_d:
#     entry['total_despatch_qty'] = entry['opening_qty'] + entry['production_out_quantity']
# else:
#     entry['total_despatch_qty'] = entry['opening_qty']
#     entry['production_remaining_quantity'] = entry['total_despatch_qty'] - entry['production_quantity'] 
#     entry['production_out_quantity'] = 0

# entry['total_weight'] = entry['weight_per_unit'] * entry['production_quantity']
# entry['total_balance_weight'] = entry['weight_per_unit'] * entry['total_despatch_qty']

#     if group_by == "Group By Supplier":
#         sorted_data = sorted(data, key=lambda x: x['supplier_name'])
#         subtotal = {
#             'challan_date': None,
#             'challan_no': None,
#             'supplier_name': None,
#             'raw_item_code': 'Subtotal',
#             'raw_item_name': None,
#             'ok_quantity': 0.0,
#             'cr_quantity': 0.0,
#             'mr_quantity': 0.0,
#             'rw_quantity': 0.0,
#             'production_quantity': 0.0,
#             'production_out_quantity': 0.0,
#             'production_remaining_quantity': 0.0
#         }
#         result = []
#         current_supplier = None
#         for entry in sorted_data:
#             if entry['supplier_name'] != current_supplier:
#                 if current_supplier is not None:
#                     result.append(subtotal.copy())
#                     subtotal = subtotal.fromkeys(subtotal, 0.0)
#                     subtotal['raw_item_code'] = 'Subtotal'
#                 current_supplier = entry['supplier_name']
#                 subtotal['supplier_name'] = None
#             for key in subtotal.keys():
#                 if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
#                     subtotal[key] += entry[key]
#             result.append(entry)
#         result.append(subtotal)

#     if group_by == "Group By Item":
#         sorted_data = sorted(data, key=lambda x: x['supplier_name'])
#         sorted_data = sorted(sorted_data, key=lambda x: x['raw_item_code'])
#         subtotal = {
#             'challan_date': None,
#             'challan_no': None,
#             'supplier_name': None,
#             'raw_item_code': 'Subtotal',
#             'raw_item_name': None,
#             'ok_quantity': 0.0,
#             'cr_quantity': 0.0,
#             'mr_quantity': 0.0,
#             'rw_quantity': 0.0,
#             'production_quantity': 0.0,
#             'production_out_quantity': 0.0,
#             'production_remaining_quantity': 0.0
#         }
#         result = []
#         current_item_code = None
#         for entry in sorted_data:
#             if entry['raw_item_code'] != current_item_code:
#                 if current_item_code is not None:
#                     result.append(subtotal.copy())
#                     subtotal = subtotal.fromkeys(subtotal, 0.0)
#                     subtotal['supplier_name'] = 'Subtotal'
#                 current_item_code = entry['raw_item_code']
#                 subtotal['raw_item_code'] = None
#             for key in subtotal.keys():
#                 if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
#                     subtotal[key] += entry[key]
#             result.append(entry)
#         result.append(subtotal)
#     return result

# def add_subtotal(data):
    # subtotal = {
    #     'challan_date': None,
    #     'challan_no': None,
    #     'supplier_name': None,
    #     'raw_item_code': 'Subtotal',
    #     'raw_item_name': None,
    #     'ok_quantity': 0.0,
    #     'cr_quantity': 0.0,
    #     'mr_quantity': 0.0,
    #     'rw_quantity': 0.0,
    #     'production_quantity': 0.0,
    #     'production_out_quantity': 0.0,
    #     'production_remaining_quantity': 0.0
    # }
    # result = []
    # current_supplier = None
    
    # for entry in data:
    #     if entry['supplier_name'] != current_supplier:
    #         if current_supplier is not None:
    #             result.append(subtotal.copy())
    #             subtotal = subtotal.fromkeys(subtotal, 0.0)
    #             subtotal['raw_item_code'] = 'Subtotal'
    #         current_supplier = entry['supplier_name']
    #         subtotal['supplier_name'] = None
        
    #     for key in subtotal.keys():
    #         if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
    #             subtotal[key] += entry[key]

    #     result.append(entry)
    
    # result.append(subtotal)
    # return result

#----------------------------------------------------------------SQL FOR BOTH--------------------------------------------------------------------#


  # sql_query = """
    #             SELECT sc.posting_date AS Date, bos.subcontracting ,sc.supplier_name, bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity, bos.rw_quantity, bos.production_quantity, bos.production_out_quantity,bos.weight_per_unit,
    #             (bos.production_out_quantity - bos.production_quantity) as production_remaining_quantity
    #             FROM `tabBifurcation Out Subcontracting` as bos
    #             LEFT JOIN `tabSubcontracting` sc on sc.name = bos.parent
    #             WHERE sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1
    #             """
    # sql_query1 = """
    #             SELECT sc.posting_date AS Date, sc.name as subcontracting,sc.supplier_name, bos.raw_item_code, bos.raw_item_name, 0 ok_quantity, 0 cr_quantity, 0 mr_quantity, 0 rw_quantity, 0 production_quantity, bos.production_quantity as production_out_quantity, bos.weight_per_unit,
    #             0 production_remaining_quantity
    #             FROM `tabSubcontracting` as sc
    #             LEFT JOIN `tabItems Subcontracting` bos on sc.name = bos.parent
    #             WHERE sc.in_or_out ='OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 GROUP BY bos.raw_item_code
    #             """


#----------------------------------------------------------------SQL FOR UNION--------------------------------------------------------------------#


    # sql_query = """
    #             SELECT 
    #             Date, 
    #             subcontracting, 
    #             supplier_name, 
    #             raw_item_code, 
    #             raw_item_name, 
    #             ok_quantity, 
    #             cr_quantity, 
    #             mr_quantity, 
    #             rw_quantity, 
    #             (ok_quantity + cr_quantity + mr_quantity + rw_quantity) as production_quantity, 
    #             production_out_quantity, 
    #             weight_per_unit, 
    #             production_remaining_quantity
    #         FROM (
    #             SELECT 
    #                 sc.posting_date AS Date, 
    #                 bos.subcontracting, 
    #                 sc.supplier_name, 
    #                 bos.raw_item_code, 
    #                 bos.raw_item_name, 
    #                 bos.ok_quantity, 
    #                 bos.cr_quantity, 
    #                 bos.mr_quantity, 
    #                 bos.rw_quantity, 
    #                 bos.production_quantity, 
    #                 bos.production_out_quantity, 
    #                 bos.weight_per_unit,
    #                 (bos.production_out_quantity - bos.production_quantity) AS production_remaining_quantity
    #             FROM 
    #                 `tabBifurcation Out Subcontracting` AS bos
    #             LEFT JOIN 
    #                 `tabSubcontracting` sc ON sc.name = bos.parent
    #             WHERE 
    #                 sc.company = %s 
    #                 AND DATE(sc.posting_date) BETWEEN %s AND %s 
    #                 AND sc.docstatus = 1
                
    #             UNION ALL
                
    #             SELECT 
    #                 sc.posting_date AS Date, 
    #                 sc.name AS subcontracting, 
    #                 sc.supplier_name, 
    #                 bos.raw_item_code, 
    #                 bos.raw_item_name, 
    #                 0 AS ok_quantity, 
    #                 0 AS cr_quantity, 
    #                 0 AS mr_quantity, 
    #                 0 AS rw_quantity, 
    #                 bos.production_quantity, 
    #                 bos.production_quantity AS production_out_quantity, 
    #                 bos.weight_per_unit,
    #                 0 AS production_remaining_quantity
    #             FROM 
    #                 `tabSubcontracting` AS sc
    #             LEFT JOIN 
    #                 `tabItems Subcontracting` bos ON sc.name = bos.parent
    #             WHERE 
    #                 sc.in_or_out = 'OUT' 
    #                 AND sc.company = %s 
    #                 AND DATE(sc.posting_date) BETWEEN %s AND %s 
    #                 AND sc.docstatus = 1
    #         ) AS combined_results
    #             """

# # Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
# # For license information, please see license.txt

# import frappe
# from datetime import datetime

# def execute(filters=None):
#     columns, data = [], {}
#     columns = get_col(filters)
#     data = get_data(filters)
#     return columns, data

# def get_col(filters):
#     columns = [
#         # {
#         #     "fieldname": "Date","fieldtype": "Date","label": "Posting Date"
#         # },
#         {
#             "fieldname": "supplier_name","fieldtype": "Data","label": "Supplier Name"
#         },
#         {
#             "fieldname": "opening_qty","fieldtype": "Data","label": "Opening QTY",
#         },
#         {
#             "fieldname": "production_out_quantity","fieldtype": "Data","label": "Dispatch QTY"
#         },
#         {
#             "fieldname": "total_despatch_qty","fieldtype": "Data","label": "Total Dispatch QTY",
#         },
#         {
#             "fieldname": "ok_quantity","fieldtype": "Float","label": "Ok QTY"
#         },
#         {
#             "fieldname": "cr_quantity","fieldtype": "Float","label": "CR QTY"
#         },
#         {
#             "fieldname": "mr_quantity","fieldtype": "Float","label": "MR QTY"
#         },
#         {
#             "fieldname": "as_it_is_quantity","fieldtype": "Float","label": "AS IT IS QTY"
#         },
#         {
#             "fieldname": "rw_quantity","fieldtype": "Float","label": "RW QTY"
#         },
#         {
#             "fieldname": "prod_quantity","fieldtype": "Float","label": "Total Receipts"
#         },
#         {
#             "fieldname": "production_remaining_quantity","fieldtype": "Float","label": "Balance"
#         }
#     ]

#     if filters.get("group_by") == "Group By Item":
#         columns.insert(0, {"fieldname": "raw_item_code","fieldtype": "Data","label": "Raw Item Code"})
#         columns.insert(1,{"fieldname": "raw_item_name","fieldtype": "Data","label": "Raw Item Name"})
#     else:
#         columns.insert(1, {"fieldname": "raw_item_code","fieldtype": "Data","label": "Raw Item Code"})
#         columns.insert(2,{"fieldname": "raw_item_name","fieldtype": "Data","label": "Raw Item Name"})

#     if filters.get("include_weight") == 1:
#         columns.append({"fieldname": "weight_per_unit","fieldtype": "Float","label": "Wt/Pc"})
#         columns.append({"fieldname": "total_weight","fieldtype": "Float","label": "Total Receipts Weight"})
#         columns.append({"fieldname": "total_balance_weight","fieldtype": "Float","label": "Total Balance Weight"})

#     return columns

# def get_data(filters):
#     from_date = filters.get("from_date")
#     to_date = filters.get("to_date")
#     sup_id = filters.get("supplier_id")
#     comp = filters.get("company")
#     item = filters.get("item")
#     group_by = filters.get("group_by")

#     sql_query = """
#             SELECT 
#                 Date, 
#                 warehouse, 
#                 supplier_name, 
#                 raw_item_code, 
#                 raw_item_name, 
#                 SUM(ok_quantity) AS ok_quantity, 
#                 SUM(cr_quantity) AS cr_quantity, 
#                 SUM(mr_quantity) AS mr_quantity, 
#                 SUM(as_it_is_quantity) AS as_it_is_quantity, 
#                 SUM(rw_quantity) AS rw_quantity, 
#                 SUM(prod_quantity) AS prod_quantity, 
#                 SUM(production_out_quantity) AS production_out_quantity, 
#                 weight_per_unit, 
#                 0 AS production_remaining_quantity
#             FROM (
#                 SELECT 
#                     sc.posting_date AS Date, 
#                     sc.source_warehouse AS warehouse, 
#                     sc.supplier_name, 
#                     bos.raw_item_code, 
#                     bos.raw_item_name, 
#                     bos.ok_quantity, 
#                     bos.cr_quantity, 
#                     bos.mr_quantity, 
#                     bos.as_it_is_quantity, 
#                     bos.rw_quantity, 
#                     (bos.ok_quantity + bos.cr_quantity + bos.mr_quantity + bos.as_it_is_quantity + bos.rw_quantity) AS prod_quantity, 
#                     0 AS production_out_quantity, 
#                     bos.weight_per_unit, 
#                     0 AS production_remaining_quantity
#                 FROM 
#                     `tabBifurcation Out Subcontracting` AS bos
#                 INNER JOIN 
#                     `tabSubcontracting` sc ON sc.name = bos.parent
#                 WHERE 
#                     sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}

#                 UNION ALL

#                 SELECT 
#                     sc.posting_date AS Date, 
#                     sc.target_warehouse AS warehouse, 
#                     sc.supplier_name, 
#                     bos.raw_item_code, 
#                     bos.raw_item_name, 
#                     0 AS ok_quantity, 
#                     0 AS cr_quantity, 
#                     0 AS mr_quantity, 
#                     0 AS as_it_is_quantity, 
#                     0 AS rw_quantity, 
#                     0 AS prod_quantity, 
#                     bos.production_quantity AS production_out_quantity, 
#                     bos.weight_per_unit, 
#                     0 AS production_remaining_quantity
#                 FROM 
#                     `tabSubcontracting` AS sc
#                 INNER JOIN 
#                     `tabItems Subcontracting` bos ON sc.name = bos.parent
#                 WHERE 
#                     sc.in_or_out = 'OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
#             ) AS combined_results
#             GROUP BY  
#                 warehouse,
#                 supplier_name, 
#                 raw_item_code, 
#                 raw_item_name, 
#                 weight_per_unit;
#             """


#     conditions = []
#     params = [comp, from_date, to_date]

#     if item:
#         conditions.append("bos.raw_item_code = %s")
#         params.append(item)

#     if sup_id:
#         conditions.append("sc.supplier_id = %s")
#         params.append(sup_id)

#     params = param(params, comp, from_date, to_date)

#     if item:
#         params.append(item)

#     if sup_id:
#         params.append(sup_id)

#     cond = " AND " + " AND ".join(conditions) if conditions else ""
#     sql_query = sql_query.format(condition = cond)

#     data = frappe.db.sql(sql_query, tuple(params), as_dict=True)
#     # frappe.throw(str(data))

#     for entry in data:
#         # warehouse = frappe.get_value("Subcontracting", {'name': entry['subcontracting'], 'in_or_out':'OUT'},'target_warehouse')
#         warehouse = entry['warehouse']
#         # frappe.msgprint(str(warehouse))
#         opening_qty = get_all_available_quantity(entry['raw_item_code'], warehouse, filters)
#         entry['opening_qty'] = opening_qty
#         entry['total_despatch_qty'] = entry['opening_qty'] + entry['production_out_quantity']
#         entry['total_weight'] = entry['weight_per_unit'] * entry['prod_quantity']
#         entry['total_balance_weight'] = entry['weight_per_unit'] * entry['total_despatch_qty']
#         entry['production_remaining_quantity'] = entry['total_despatch_qty'] - entry['prod_quantity']


#     if group_by == "Group By Supplier":
#         sorted_data = sorted(data, key=lambda x: x['supplier_name'])
#         subtotal = {
#             'supplier_name': None,
#             'raw_item_code': 'Subtotal',
#             'raw_item_name': None,
#             'opening_qty': 0.0,
#             'total_despatch_qty': 0,
#             'ok_quantity': 0.0,
#             'cr_quantity': 0.0,
#             'mr_quantity': 0.0,
#             'as_it_is_quantity': 0.0,
#             'rw_quantity': 0.0,
#             'prod_quantity': 0.0,
#             'production_out_quantity': 0.0,
#             'production_remaining_quantity': 0.0,
#             'weight_per_unit': 0.0,
#             'total_weight': 0.0,
#             'total_balance_weight': 0.0
#         }
#         result = []
#         current_supplier = None
#         for entry in sorted_data:
#             if entry['supplier_name'] != current_supplier:
#                 if current_supplier is not None:
#                     result.append(subtotal.copy())
#                     subtotal = subtotal.fromkeys(subtotal, 0.0)
#                     subtotal['raw_item_code'] = 'Subtotal'
#                 current_supplier = entry['supplier_name']
#                 subtotal['supplier_name'] = None
#             for key in subtotal.keys():
#                 if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
#                     subtotal[key] += entry[key]
#             result.append(entry)
#         result.append(subtotal)

#     if group_by == "Group By Item":
#         sorted_data = sorted(data, key=lambda x: x['supplier_name'])
#         sorted_data = sorted(sorted_data, key=lambda x: x['raw_item_code'])
#         subtotal = {
#             'supplier_name': None,
#             'raw_item_code': 'Subtotal',
#             'raw_item_name': None,
#             'opening_qty': 0.0,
#             'total_despatch_qty': 0,
#             'ok_quantity': 0.0,
#             'cr_quantity': 0.0,
#             'mr_quantity': 0.0,
#             'as_it_is_quantity': 0.0,
#             'rw_quantity': 0.0,
#             'prod_quantity': 0.0,
#             'production_out_quantity': 0.0,
#             'production_remaining_quantity': 0.0,
#             'weight_per_unit': 0.0,
#             'total_weight': 0.0,
#             'total_balance_weight': 0.0
#         }
#         result = []
#         current_item_code = None
#         for entry in sorted_data:
#             if entry['raw_item_code'] != current_item_code:
#                 if current_item_code is not None:
#                     subtotal['supplier_name'] = 'Subtotal'
#                     result.append(subtotal.copy())
#                     subtotal = subtotal.fromkeys(subtotal, 0.0)
#                     subtotal['supplier_name'] = 'Subtotal'
#                 current_item_code = entry['raw_item_code']
#                 subtotal['raw_item_code'] = None
#             for key in subtotal.keys():
#                 if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
#                     subtotal[key] += entry[key]
#             result.append(entry)
#         result.append(subtotal)
#     return result

# def param(params, comp, from_date, to_date):
#     params.append(comp)
#     params.append(from_date)
#     params.append(to_date)
#     return params

# def get_all_available_quantity(item_code, warehouse, filters): 
#     from_date, to_date = filters.get('from_date'), filters.get('to_date')
#     company_name = filters.get('company')

#     opn_sum = 0
#     opening_balance = frappe.db.sql("""
#             SELECT qty_after_transaction 
#             FROM `tabStock Ledger Entry` 
#             WHERE posting_date < '{0}' 
#                 AND warehouse = '{1}' 
#                 AND item_code = '{2}' 
#                 AND company = '{3}' 
#                 AND is_cancelled='{4}'
#             ORDER BY creation DESC 
#             LIMIT 1
#             """.format(from_date, warehouse, item_code, company_name, False), as_dict=True)
#     if opening_balance:
#         opn_sum = opening_balance[0].qty_after_transaction
#     return opn_sum




# # sql_query = """
# #     SELECT Date, warehouse, supplier_name, raw_item_code, raw_item_name, SUM(ok_quantity) AS ok_quantity, SUM(cr_quantity) AS cr_quantity, SUM(mr_quantity) AS mr_quantity, SUM(as_it_is_quantity) AS as_it_is_quantity, SUM(rw_quantity) AS rw_quantity, SUM(production_quantity) AS production_quantity, SUM(production_out_quantity) AS production_out_quantity, weight_per_unit, 0 AS production_remaining_quantity
# # FROM (
# #     SELECT sc.posting_date AS Date, sc.source_warehouse as warehouse, sc.supplier_name, bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity, bos.as_it_is_quantity, bos.rw_quantity, (bos.ok_quantity+bos.cr_quantity+bos.mr_quantity+bos.as_it_is_quantity+bos.rw_quantity) as production_quantity, bos.production_out_quantity, bos.weight_per_unit,production_remaining_quantity
# #     FROM 
# #         `tabBifurcation Out Subcontracting` AS bos
# #     INNER JOIN 
# #         `tabSubcontracting` sc ON sc.name = bos.parent
# #     WHERE 
# #         sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
        
# #     UNION ALL

# #     SELECT sc.posting_date AS Date, sc.target_warehouse as warehouse, sc.supplier_name, bos.raw_item_code, bos.raw_item_name, 0 AS ok_quantity, 0 AS cr_quantity, 0 AS mr_quantity,0 AS as_it_is_quantity, 0 AS rw_quantity, 0 AS production_quantity, bos.production_quantity AS production_out_quantity, bos.weight_per_unit,0 AS production_remaining_quantity
# #     FROM 
# #         `tabSubcontracting` AS sc
# #     INNER JOIN 
# #         `tabItems Subcontracting` bos ON sc.name = bos.parent
# #     WHERE sc.in_or_out = 'OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
# # ) AS combined_results
# # GROUP BY  
# #     warehouse,
# #     supplier_name, 
# #     raw_item_code, 
# #     raw_item_name, 
# #     weight_per_unit;
# #     """











# # def get_data(filters):
# #     from_date = filters.get("from_date")
# #     to_date = filters.get("to_date")
# #     sup_id = filters.get("supplier_id")
# #     comp = filters.get("company")
# #     item = filters.get("item")
# #     group_by = filters.get("group_by")

# #     sql_query = """
# #                 SELECT sc.supplier_name, bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity, bos.rw_quantity, bos.production_quantity, bos.production_out_quantity,
# #                 (bos.production_out_quantity - bos.production_quantity) as production_remaining_quantity
# #                 FROM `tabBifurcation Out Subcontracting` as bos
# #                 LEFT JOIN `tabSubcontracting` sc on sc.name = bos.parent
# #                 WHERE sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1
# #                 """
# #     result = get_all_available_quantity(bos.raw_item_code, filters)
# #     frappe.throw(str(result))
    
# #     conditions = []
# #     params = [comp, from_date, to_date]

# #     if item:
# #         conditions.append("bos.raw_item_code = %s")
# #         params.append(item)

# #     if sup_id:
# #         conditions.append("sc.supplier_id = %s")
# #         params.append(sup_id)

# #     sql_query += " AND " + " AND ".join(conditions) if conditions else ""
# #     data = frappe.db.sql(sql_query, tuple(params), as_dict=True)
# #     # frappe.throw(str(data))

# # posting_date = frappe.get_value("Subcontracting",{'name': entry['subcontracting'], 'in_or_out':'OUT'},'posting_date')
# # from_d, to_d, post_d = datetime.strptime(from_date, "%Y-%m-%d"), datetime.strptime(to_date, "%Y-%m-%d"), datetime.strptime(str(posting_date), "%Y-%m-%d")
# # if from_d <= post_d <= to_d:
# #     entry['total_despatch_qty'] = entry['opening_qty'] + entry['production_out_quantity']
# # else:
# #     entry['total_despatch_qty'] = entry['opening_qty']
# #     entry['production_remaining_quantity'] = entry['total_despatch_qty'] - entry['production_quantity'] 
# #     entry['production_out_quantity'] = 0

# # entry['total_weight'] = entry['weight_per_unit'] * entry['production_quantity']
# # entry['total_balance_weight'] = entry['weight_per_unit'] * entry['total_despatch_qty']

# #     if group_by == "Group By Supplier":
# #         sorted_data = sorted(data, key=lambda x: x['supplier_name'])
# #         subtotal = {
# #             'challan_date': None,
# #             'challan_no': None,
# #             'supplier_name': None,
# #             'raw_item_code': 'Subtotal',
# #             'raw_item_name': None,
# #             'ok_quantity': 0.0,
# #             'cr_quantity': 0.0,
# #             'mr_quantity': 0.0,
# #             'rw_quantity': 0.0,
# #             'production_quantity': 0.0,
# #             'production_out_quantity': 0.0,
# #             'production_remaining_quantity': 0.0
# #         }
# #         result = []
# #         current_supplier = None
# #         for entry in sorted_data:
# #             if entry['supplier_name'] != current_supplier:
# #                 if current_supplier is not None:
# #                     result.append(subtotal.copy())
# #                     subtotal = subtotal.fromkeys(subtotal, 0.0)
# #                     subtotal['raw_item_code'] = 'Subtotal'
# #                 current_supplier = entry['supplier_name']
# #                 subtotal['supplier_name'] = None
# #             for key in subtotal.keys():
# #                 if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
# #                     subtotal[key] += entry[key]
# #             result.append(entry)
# #         result.append(subtotal)

# #     if group_by == "Group By Item":
# #         sorted_data = sorted(data, key=lambda x: x['supplier_name'])
# #         sorted_data = sorted(sorted_data, key=lambda x: x['raw_item_code'])
# #         subtotal = {
# #             'challan_date': None,
# #             'challan_no': None,
# #             'supplier_name': None,
# #             'raw_item_code': 'Subtotal',
# #             'raw_item_name': None,
# #             'ok_quantity': 0.0,
# #             'cr_quantity': 0.0,
# #             'mr_quantity': 0.0,
# #             'rw_quantity': 0.0,
# #             'production_quantity': 0.0,
# #             'production_out_quantity': 0.0,
# #             'production_remaining_quantity': 0.0
# #         }
# #         result = []
# #         current_item_code = None
# #         for entry in sorted_data:
# #             if entry['raw_item_code'] != current_item_code:
# #                 if current_item_code is not None:
# #                     result.append(subtotal.copy())
# #                     subtotal = subtotal.fromkeys(subtotal, 0.0)
# #                     subtotal['supplier_name'] = 'Subtotal'
# #                 current_item_code = entry['raw_item_code']
# #                 subtotal['raw_item_code'] = None
# #             for key in subtotal.keys():
# #                 if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
# #                     subtotal[key] += entry[key]
# #             result.append(entry)
# #         result.append(subtotal)
# #     return result

# # def add_subtotal(data):
#     # subtotal = {
#     #     'challan_date': None,
#     #     'challan_no': None,
#     #     'supplier_name': None,
#     #     'raw_item_code': 'Subtotal',
#     #     'raw_item_name': None,
#     #     'ok_quantity': 0.0,
#     #     'cr_quantity': 0.0,
#     #     'mr_quantity': 0.0,
#     #     'rw_quantity': 0.0,
#     #     'production_quantity': 0.0,
#     #     'production_out_quantity': 0.0,
#     #     'production_remaining_quantity': 0.0
#     # }
#     # result = []
#     # current_supplier = None
    
#     # for entry in data:
#     #     if entry['supplier_name'] != current_supplier:
#     #         if current_supplier is not None:
#     #             result.append(subtotal.copy())
#     #             subtotal = subtotal.fromkeys(subtotal, 0.0)
#     #             subtotal['raw_item_code'] = 'Subtotal'
#     #         current_supplier = entry['supplier_name']
#     #         subtotal['supplier_name'] = None
        
#     #     for key in subtotal.keys():
#     #         if key not in ['supplier_name', 'raw_item_code', 'challan_date', 'raw_item_name', 'challan_no']:
#     #             subtotal[key] += entry[key]

#     #     result.append(entry)
    
#     # result.append(subtotal)
#     # return result

# #----------------------------------------------------------------SQL FOR BOTH--------------------------------------------------------------------#


#   # sql_query = """
#     #             SELECT sc.posting_date AS Date, bos.subcontracting ,sc.supplier_name, bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity, bos.rw_quantity, bos.production_quantity, bos.production_out_quantity,bos.weight_per_unit,
#     #             (bos.production_out_quantity - bos.production_quantity) as production_remaining_quantity
#     #             FROM `tabBifurcation Out Subcontracting` as bos
#     #             LEFT JOIN `tabSubcontracting` sc on sc.name = bos.parent
#     #             WHERE sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1
#     #             """
#     # sql_query1 = """
#     #             SELECT sc.posting_date AS Date, sc.name as subcontracting,sc.supplier_name, bos.raw_item_code, bos.raw_item_name, 0 ok_quantity, 0 cr_quantity, 0 mr_quantity, 0 rw_quantity, 0 production_quantity, bos.production_quantity as production_out_quantity, bos.weight_per_unit,
#     #             0 production_remaining_quantity
#     #             FROM `tabSubcontracting` as sc
#     #             LEFT JOIN `tabItems Subcontracting` bos on sc.name = bos.parent
#     #             WHERE sc.in_or_out ='OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 GROUP BY bos.raw_item_code
#     #             """


# #----------------------------------------------------------------SQL FOR UNION--------------------------------------------------------------------#


#     # sql_query = """
#     #             SELECT 
#     #             Date, 
#     #             subcontracting, 
#     #             supplier_name, 
#     #             raw_item_code, 
#     #             raw_item_name, 
#     #             ok_quantity, 
#     #             cr_quantity, 
#     #             mr_quantity, 
#     #             rw_quantity, 
#     #             (ok_quantity + cr_quantity + mr_quantity + rw_quantity) as production_quantity, 
#     #             production_out_quantity, 
#     #             weight_per_unit, 
#     #             production_remaining_quantity
#     #         FROM (
#     #             SELECT 
#     #                 sc.posting_date AS Date, 
#     #                 bos.subcontracting, 
#     #                 sc.supplier_name, 
#     #                 bos.raw_item_code, 
#     #                 bos.raw_item_name, 
#     #                 bos.ok_quantity, 
#     #                 bos.cr_quantity, 
#     #                 bos.mr_quantity, 
#     #                 bos.rw_quantity, 
#     #                 bos.production_quantity, 
#     #                 bos.production_out_quantity, 
#     #                 bos.weight_per_unit,
#     #                 (bos.production_out_quantity - bos.production_quantity) AS production_remaining_quantity
#     #             FROM 
#     #                 `tabBifurcation Out Subcontracting` AS bos
#     #             LEFT JOIN 
#     #                 `tabSubcontracting` sc ON sc.name = bos.parent
#     #             WHERE 
#     #                 sc.company = %s 
#     #                 AND DATE(sc.posting_date) BETWEEN %s AND %s 
#     #                 AND sc.docstatus = 1
                
#     #             UNION ALL
                
#     #             SELECT 
#     #                 sc.posting_date AS Date, 
#     #                 sc.name AS subcontracting, 
#     #                 sc.supplier_name, 
#     #                 bos.raw_item_code, 
#     #                 bos.raw_item_name, 
#     #                 0 AS ok_quantity, 
#     #                 0 AS cr_quantity, 
#     #                 0 AS mr_quantity, 
#     #                 0 AS rw_quantity, 
#     #                 bos.production_quantity, 
#     #                 bos.production_quantity AS production_out_quantity, 
#     #                 bos.weight_per_unit,
#     #                 0 AS production_remaining_quantity
#     #             FROM 
#     #                 `tabSubcontracting` AS sc
#     #             LEFT JOIN 
#     #                 `tabItems Subcontracting` bos ON sc.name = bos.parent
#     #             WHERE 
#     #                 sc.in_or_out = 'OUT' 
#     #                 AND sc.company = %s 
#     #                 AND DATE(sc.posting_date) BETWEEN %s AND %s 
#     #                 AND sc.docstatus = 1
#     #         ) AS combined_results
#     #             """