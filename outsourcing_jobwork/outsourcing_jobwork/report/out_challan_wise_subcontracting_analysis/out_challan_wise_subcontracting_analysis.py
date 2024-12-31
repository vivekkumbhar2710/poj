# Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict

def execute(filters=None):
    columns, data = [], []
    columns = get_col(filters)
    data = get_data(filters)
    return columns, data

def get_col(filters):
    columns = [
        {"fieldname": "out_date", "fieldtype": "Date", "label": "OUT Challan Date"},
        {"fieldname": "supplier", "fieldtype": "Data", "label": "Supplier"},
        {"fieldname": "supplier_name", "fieldtype": "Data", "label": "Supplier Name"},
        {"fieldname": "out_challan_no", "fieldtype": "Link", "label": "OUT Challan", "options": "Subcontracting"},
        {"fieldname": "out_item", "fieldtype": "Link", "label": "Out Item", "options": "Item"},
        {"fieldname": "out_item_qty", "fieldtype": "Float", "label": "Out Item Qty"},
        {"fieldname": "in_date", "fieldtype": "Date", "label": "In Challan Date"},
        {"fieldname": "in_challan_no", "fieldtype": "Link", "label": "IN Challan", "options": "Subcontracting"},
        {"fieldname": "in_item", "fieldtype": "Link", "label": "IN Item", "options": "Item"},
        {"fieldname": "ok_quantity", "fieldtype": "Float", "label": "OK Qty"},
        {"fieldname": "cr_quantity", "fieldtype": "Float", "label": "CR Qty"},
        {"fieldname": "mr_quantity", "fieldtype": "Float", "label": "MR Qty"},
        {"fieldname": "rw_quantity", "fieldtype": "Float", "label": "RW Qty"},
        {"fieldname": "as_it_is_quantity", "fieldtype": "Float", "label": "AS IT IS Qty"},
        {"fieldname": "in_item_qty", "fieldtype": "Float", "label": "IN Item Qty"},
        {"fieldname": "balance", "fieldtype": "Float", "label": "Balance"},
        {"fieldname": "days", "fieldtype": "Data", "label": "No. Of Days"},
    ]
    return columns

def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    comp = filters.get("company")
    out_challan_no = filters.get("out_challan_no")
    out_item = filters.get("out_item")
    supplier = filters.get("supplier")

    sql_query = """
                SELECT 
                    so.posting_date as out_date,so.supplier_id as supplier,so.supplier_name as supplier_name, so.name as out_challan_no, i.raw_item_code as out_item,
                    i.production_quantity as out_item_qty, si.posting_date as in_date, si.name as in_challan_no, bos.raw_item_code as in_item,
                    bos.ok_quantity as ok_quantity,bos.cr_quantity as cr_quantity,bos.mr_quantity as mr_quantity,
                    bos.rw_quantity as rw_quantity,bos.as_it_is_quantity as as_it_is_quantity,
                    (bos.ok_quantity + bos.cr_quantity + bos.mr_quantity + bos.rw_quantity + bos.as_it_is_quantity) as in_item_qty,
                    (i.production_quantity - (bos.ok_quantity + bos.cr_quantity + bos.mr_quantity + bos.rw_quantity + bos.as_it_is_quantity)) as balance,
                    DATEDIFF(si.posting_date, so.posting_date) as days
                FROM 
                    `tabSubcontracting` so 
                LEFT JOIN 
                    `tabItems Subcontracting` i ON so.name = i.parent
                LEFT JOIN 
                    `tabBifurcation Out Subcontracting` bos ON i.raw_item_code = bos.raw_item_code 
                LEFT JOIN 
                    `tabSubcontracting` si ON bos.parent = si.name AND si.in_or_out = 'IN' AND si.docstatus = 1 AND si.company = %s
                WHERE 
                    so.in_or_out = 'OUT' AND so.posting_date BETWEEN %s AND %s AND so.docstatus = 1 AND so.company = %s 
                    AND i.raw_item_code = bos.raw_item_code AND si.name IS NOT NULL AND bos.subcontracting = so.name
                    AND (bos.ok_quantity + bos.cr_quantity + bos.mr_quantity + bos.rw_quantity + bos.as_it_is_quantity) > 0.0
    """
    if out_challan_no:
        sql_query += " AND so.name = %s"
    if out_item:
        sql_query += " AND i.raw_item_code = %s"
    if supplier:
        sql_query += " AND so.supplier_id = %s"
    sql_query += " ORDER BY out_challan_no, out_item, in_challan_no"
    params = [comp, from_date, to_date, comp]
    if out_challan_no:
        params.append(out_challan_no)
    if out_item:
        params.append(out_item)
    if supplier:
        params.append(supplier)
    data = frappe.db.sql(sql_query, params, as_dict=True)
    result = []
    prev_dt =  None
    prev_dt_item =  None
    total_in_qty = 0
    total_out_qty = 0
    tot = 0
    for dt in data:
        if not prev_dt and not prev_dt_item:
            prev_dt = dt['out_challan_no']
            prev_dt_item = dt['out_item']
            total_in_qty = total_in_qty + dt['in_item_qty']
            total_out_qty = dt['out_item_qty']
            tot += dt['out_item_qty']
            result.append(dt)
        else:
            current_dt = dt['out_challan_no']
            current_dt_item = dt['out_item']
            if prev_dt == current_dt and prev_dt_item == current_dt_item:
                total_in_qty = total_in_qty + dt['in_item_qty']
                total_out_qty = dt['out_item_qty']
                result.append({'out_date': '','supplier': '','supplier_name': '', 'out_challan_no': '', 'out_item': '', 'out_item_qty': '', 'in_date': dt['in_date'], 'in_challan_no': dt['in_challan_no'],'ok_quantity': dt['ok_quantity'],'cr_quantity': dt['cr_quantity'],'mr_quantity': dt['mr_quantity'],'rw_quantity': dt['rw_quantity'],'as_it_is_quantity': dt['as_it_is_quantity'],'in_item': dt['in_item'], 'in_item_qty': dt['in_item_qty'],'balance': total_out_qty - total_in_qty, 'days': dt['days']})
            else:
                result.append({'out_date': '','supplier': '<b>Sub Total</b>','supplier_name': '', 'out_challan_no': '', 'out_item': '', 'out_item_qty': total_out_qty, 'in_date': '', 'in_challan_no': '','ok_quantity': '','cr_quantity': '','mr_quantity': '','rw_quantity': '','in_item': '', 'in_item_qty': total_in_qty, 'days': ''})
                total_in_qty = dt['in_item_qty']
                total_out_qty = dt['out_item_qty']
                tot += total_out_qty
                result.append(dt)
            prev_dt = current_dt
            prev_dt_item = current_dt_item
    result.append({'out_date': '','supplier': '<b>Sub Total</b>','supplier_name': '', 'out_challan_no': '', 'out_item': '', 'out_item_qty': total_out_qty, 'in_date': '', 'in_challan_no': '','ok_quantity': '','cr_quantity': '','mr_quantity': '','rw_quantity': '','in_item': '', 'in_item_qty': total_in_qty, 'days': ''})
    result.append({'supplier': '<b>Total</b>', 'out_item_qty': tot})
    return result


# result = []
# grouped_data = defaultdict(list)

# for row in data:
#     key = (row['out_date'], row['out_challan_no'], row['out_item'], row['out_item_qty'])
#     grouped_data[key].append(row)

# for key, items in grouped_data.items():
#     out_date, out_challan_no, out_item, out_item_qty = key
#     total_in_qty = sum(item['in_item_qty'] for item in items)
#     for item in items:
#         result.append({
#             "out_date": out_date,
#             "out_challan_no": out_challan_no,
#             "out_item": out_item,
#             "out_item_qty": out_item_qty,
#             "in_date": item['in_date'],
#             "in_challan_no": item['in_challan_no'],
#             "in_item": item['in_item'],
#             "in_item_qty": item['in_item_qty'],
#             "days": item['days']
#         })
#     result.append({
#         "out_date": "",
#         "out_challan_no": "",
#         "out_item": "",
#         "out_item_qty": "",
#         "in_date": "",
#         "in_challan_no": "",
#         "in_item": "",
#         "in_item_qty": total_in_qty,
#         "days": ""
#     })