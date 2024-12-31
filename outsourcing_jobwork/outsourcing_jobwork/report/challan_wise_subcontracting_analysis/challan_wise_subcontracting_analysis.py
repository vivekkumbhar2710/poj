import frappe

def execute(filters=None):
    columns, data = [], []
    columns = get_col(filters)
    data = get_data(filters)
    return columns, data

def get_col(filters):
    columns = [
        {"fieldname": "name", "fieldtype": "Link", "label": "OUT Challan", "options":"Subcontracting"},
        {"fieldname": "Against", "fieldtype": "Link", "label": "OUT Challan Against IN", "options":"Subcontracting"},
        {"fieldname": "subcontracting", "fieldtype": "Link", "label": "IN Challan", "options":"Subcontracting"},
        {"fieldname": "raw_item_code", "fieldtype": "Data", "label": "Raw Item Code"},
        {"fieldname": "raw_item_name", "fieldtype": "Data", "label": "Raw Item Name"},
        {"fieldname": "supplier_name", "fieldtype": "Data", "label": "Supplier Name"},
        {"fieldname": "opening_qty", "fieldtype": "Data", "label": "Opening QTY"},
        {"fieldname": "production_out_quantity", "fieldtype": "Data", "label": "Dispatch QTY"},
        {"fieldname": "total_despatch_qty", "fieldtype": "Data", "label": "Total Dispatch QTY"},
        {"fieldname": "ok_quantity", "fieldtype": "Float", "label": "Ok QTY"},
        {"fieldname": "cr_quantity", "fieldtype": "Float", "label": "CR QTY"},
        {"fieldname": "mr_quantity", "fieldtype": "Float", "label": "MR QTY"},
        {"fieldname": "as_it_is_quantity", "fieldtype": "Float", "label": "AS IT IS QTY"},
        {"fieldname": "rw_quantity", "fieldtype": "Float", "label": "RW QTY"},
        {"fieldname": "production_quantity", "fieldtype": "Float", "label": "Total Receipts"},
        {"fieldname": "production_remaining_quantity", "fieldtype": "Float", "label": "Balance"}
    ]

    if filters.get("include_weight") == 1:
        columns.append({"fieldname": "weight_per_unit", "fieldtype": "Float", "label": "Wt/Pc"})
        columns.append({"fieldname": "total_weight", "fieldtype": "Float", "label": "Total Receipts Weight"})
        columns.append({"fieldname": "total_balance_weight", "fieldtype": "Float", "label": "Total Balance Weight"})

    return columns

def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    comp = filters.get("company")
    name = filters.get('name')
    subcontracting = filters.get('subcontracting')

    sql_query = """
                SELECT sc.name, NULL AS subcontracting,NULL AS Against,sc.name AS sort, sc.posting_date AS Date, sc.target_warehouse AS warehouse, sc.supplier_name,
                bos.raw_item_code, bos.raw_item_name, 0 AS ok_quantity, 0 AS cr_quantity, 0 AS mr_quantity,
                0 AS as_it_is_quantity, 0 AS rw_quantity, 0 AS production_quantity, 
                bos.production_quantity AS production_out_quantity, bos.weight_per_unit, 0 AS production_remaining_quantity
                FROM `tabSubcontracting` AS sc
                LEFT JOIN `tabItems Subcontracting` bos ON sc.name = bos.parent
                WHERE sc.in_or_out = 'OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
                UNION ALL
                SELECT NULL AS name, sc.name AS subcontracting,bos.subcontracting AS Against,sc.name AS sort, sc.posting_date AS Date, sc.target_warehouse AS warehouse, sc.supplier_name,
                bos.raw_item_code, bos.raw_item_name, bos.ok_quantity AS ok_quantity, bos.cr_quantity AS cr_quantity, bos.mr_quantity AS mr_quantity,
                bos.as_it_is_quantity AS as_it_is_quantity, bos.rw_quantity AS rw_quantity, 0 AS production_quantity, 
                0 AS production_out_quantity, bos.weight_per_unit, 0 AS production_remaining_quantity
                FROM `tabSubcontracting` AS sc
                LEFT JOIN `tabBifurcation Out Subcontracting` bos ON sc.name = bos.parent
                WHERE sc.in_or_out = 'IN' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
                """

    conditions = []
    params = [comp, from_date, to_date]
    if name:
        conditions.append("sc.name = %s")
        params.append(name)
    params = params + [comp, from_date, to_date]
    if name:
        params.append(name)
    cond = " AND " + " AND ".join(conditions) if conditions else ""
    sql_query = sql_query.format(condition = cond)
    data = frappe.db.sql(sql_query, tuple(params), as_dict=True)
    # frappe.throw(str(data))
    for entry in data:
        warehouse = entry['warehouse']
        if entry['name']:
            opening_qty = get_all_available_quantity(entry['raw_item_code'], warehouse, filters)
            entry['opening_qty'] = opening_qty
        else:
            entry['opening_qty'] = 0
        entry['total_despatch_qty'] = entry['opening_qty'] + entry['production_out_quantity']
        if entry['weight_per_unit']:
            entry['total_weight'] = entry['weight_per_unit'] * entry['production_quantity']
            entry['total_balance_weight'] = entry['weight_per_unit'] * entry['total_despatch_qty']
            entry['production_remaining_quantity'] = entry['total_despatch_qty'] - entry['production_quantity']
    
    sorted_data = sorted(data, key=lambda x: x['sort'])
    return sorted_data

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
        WHERE posting_date < %s 
            AND warehouse = %s 
            AND item_code = %s 
            AND company = %s 
            AND is_cancelled = 0
        ORDER BY creation DESC 
        LIMIT 1
    """, (from_date, warehouse, item_code, company_name), as_dict=True)

    if opening_balance:
        opn_sum = opening_balance[0].qty_after_transaction
    return opn_sum


sql_query = """
        SELECT sc.name, bos.subcontracting, sc.posting_date AS Date, sc.source_warehouse AS warehouse, sc.supplier_name,
               bos.raw_item_code, bos.raw_item_name, bos.ok_quantity, bos.cr_quantity, bos.mr_quantity,
               bos.as_it_is_quantity, bos.rw_quantity, 
               (bos.ok_quantity + bos.cr_quantity + bos.mr_quantity + bos.as_it_is_quantity + bos.rw_quantity) AS production_quantity,
               bos.production_out_quantity, bos.weight_per_unit, 0 AS production_remaining_quantity
        FROM `tabBifurcation Out Subcontracting` AS bos
        LEFT JOIN `tabSubcontracting` sc ON sc.name = bos.parent
        WHERE sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}

        UNION ALL
        
        SELECT sc.name, NULL AS subcontracting, sc.posting_date AS Date, sc.target_warehouse AS warehouse, sc.supplier_name,
               bos.raw_item_code, bos.raw_item_name, 0 AS ok_quantity, 0 AS cr_quantity, 0 AS mr_quantity,
               0 AS as_it_is_quantity, 0 AS rw_quantity, 0 AS production_quantity, 
               bos.production_quantity AS production_out_quantity, bos.weight_per_unit, 0 AS production_remaining_quantity
        FROM `tabSubcontracting` AS sc
        LEFT JOIN `tabItems Subcontracting` bos ON sc.name = bos.parent
        WHERE sc.in_or_out = 'OUT' AND sc.company = %s AND DATE(sc.posting_date) BETWEEN %s AND %s AND sc.docstatus = 1 {condition}
    """