# Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MaterialMovement(Document):

	@frappe.whitelist()
	def available_qty(self):
		for row in self.get("items"):
			if row.source_warehouse and row.item_code:
				available_qty = frappe.get_value('Bin',{'item_code':row.item_code,'warehouse': row.source_warehouse}, "actual_qty")
				row.available_qty = available_qty
			# if row.qty and row.rate:
			# 	row.amount = row.qty * row.rate
 
	# @frappe.whitelist()
	# def set_party_name(self):
	# 	if self.party:
	# 		if self.party_type == "Customer":
	# 			field = 'customer_name'
	# 		elif self.party_type == "Supplier":
	# 			field = 'supplier_name'
	# 		self.party_name = frappe.db.get_value(self.party_type, {"name": self.party}, field)

	def on_submit(self):
		entry_type = "Material Transfer" if self.return_against else "Material Receipt"
		if entry_type == "Material Transfer":
			for i in self.items:
				if not i.source_warehouse:
					frappe.throw("Source Warehouse Is Mandatory")
		self.material_transfer(entry_type)
  
	def material_transfer(self,entry_type):	
		doc = frappe.new_doc("Stock Entry")
		doc.stock_entry_type = entry_type
		doc.company = self.company
		doc.set_posting_time = True
		doc.posting_date =self.date
		for i in self.get("items"):
			if(i.qty>0):
				doc.append("items", {
									"s_warehouse":i.source_warehouse,
									"t_warehouse":i.target_warehouse,
									"item_code": i.item_code,
									"qty":i.qty,
									})
		if doc.items:
			doc.custom_material_movement= self.name
			doc.insert()
			doc.save()
			doc.submit()
