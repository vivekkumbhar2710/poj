# Copyright (c) 2024, Quantbit Technologies Pvt ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

def getVal(val):
	return val if val is not None else 0

def ItemName(item_code):
	return frappe.get_value('Item', item_code , 'item_name')

def get_available_quantity(item_code, warehouse):
		result = frappe.get_value("Bin",{"item_code": item_code,"warehouse": warehouse}, "actual_qty")
		return result if result else 0
def ItemWeight(item_code):
	item_weight = frappe.get_value('Production UOM Definition',{'parent': item_code ,'uom':'Kg'}, "value_per_unit")
	return item_weight if item_weight else 0


class Subcontracting(Document):
	@frappe.whitelist()
	def before_save(self):
		if self.in_or_out == 'OUT':
			pass
			
		else:
			self.validate_entry()
			self.update_raw_list("out_subcontracting_list","check")

	@frappe.whitelist()
	def before_submit(self):
		if self.in_or_out == 'OUT':
			if self.out_entry_type == 'Material Loan Given':
				self.stock_transfer_stock_entry('loan_items_subcontracting' , 'finished_item_code' , 'production_quantity' , 'source_warehouse' , 'target_warehouse' )
			else:
				self.stock_transfer_stock_entry('items_subcontracting' , 'raw_item_code' , 'production_quantity' , 'source_warehouse' , 'target_warehouse')

			# self.update_value()
		else:
			if self.in_entry_type == 'Material Loan Given':
				self.stock_transfer_stock_entry('in_loan_items_subcontracting' , 'finished_item_code' , 'in_quantity' , 'source_warehouse' , 'target_warehouse' )
				self.loan_update_out_entry()
			else:
				self.manifacturing_stock_entry()
				self.stock_transfer_stock_entry('in_rejected_items_reasons_subcontracting' , 'raw_item_code' , 'quantity' , 'source_warehouse' , 'target_warehouse')
				self.update_out_entry()

			self.set_foundry_rejection_analysis()

	def before_cancel(self):
		self.cancel_update_out_entry()
		self.loan_cancel_update_out_entry()


# =================================================================================================== BOTH ===================================================================================================

	@frappe.whitelist()
	def set_table_data(self , table , table_field , field_data = None , qty_field = None, item_code = None , warehouse_field = None):
		items_table = self.get(table)
		for i in items_table:
			setattr(i, table_field, field_data)
			if qty_field and i.get(item_code) and i.get(warehouse_field) :
				setattr(i, qty_field, get_available_quantity(i.get(item_code), i.get(warehouse_field)))


	@frappe.whitelist()
	def set_available_qty(self , table , qty_field, item_code , warehouse_field):
		items_table = self.get(table)
		for i in items_table:
			if i.get(item_code) and i.get(warehouse_field) :
				setattr(i, qty_field, get_available_quantity(i.get(item_code), i.get(warehouse_field)))

	@frappe.whitelist() 
	def set_weight_item(self):
		for d in self.get('items_subcontracting'):
			if d.raw_item_code:
				d.weight_per_unit = ItemWeight(d.raw_item_code)
				if d.production_quantity:
					d.total_finished_weight  = getVal(d.weight_per_unit) * getVal(d.production_quantity)
				d.subcontracting_operations = self.subcontracting_operations
				if not d.source_warehouse:
					d.source_warehouse = self.source_warehouse
				if not d.target_warehouse:
					d.target_warehouse = self.target_warehouse

				rate_for_print = frappe.get_value("Subcontracting Setting",{'company': self.company},'rate_for_print')
				d.rate_for_print = getVal(rate_for_print)
				d.amount = getVal(rate_for_print) * getVal(d.total_finished_weight)
				if  d.production_quantity:
					d.rate = getVal(d.amount) / getVal(d.production_quantity)
				


	@frappe.whitelist()
	def set_operation(self):
		if self.subcontracting_operations and self.in_or_out == 'OUT':
			for d in self.get('items_subcontracting'):
				d.subcontracting_operations = self.subcontracting_operations
				
			

	@frappe.whitelist()
	def stock_transfer_stock_entry(self , table , item_code , quantity , source_warehouse , target_warehouse):
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Transfer"
		se.company = self.company
		se.set_posting_time = True
		se.posting_date = self.posting_date
		for d in self.get(table):
			if d.get(quantity):
				se.append("items",
							{
								"item_code": d.get(item_code),
								"qty": d.get(quantity),
								"s_warehouse": d.get(source_warehouse),
								"t_warehouse": d.get(target_warehouse),
							},)
		se.custom_subcontracting = self.name	
		if se.items:
			se.insert()
			se.save()
			se.submit()


	def raw_item_list(self):
		item_list = []
		if self.in_entry_type == 'Subcontracting' and self.linking_option and (self.blanket_order or self.purchase_order) :
			if self.linking_option == 'Blanket Order':
				b_o_l = []
				for i in self.blanket_order:
					b_o_l.append(str(i.blanket_order))

				doctype = 'Blanket Order Item'
				filters = {'parent':['in',b_o_l]}
				fields = ['item_code' , 'parent','custom_subcontracting_operations','rate']

			else:
				p_o_l = []
				for j in self.purchase_order:
					p_o_l.append(str(j.purchase_order))

				doctype = 'Purchase Order Item'
				filters = {'parent':['in',p_o_l]}
				fields = ['item_code' , 'parent','custom_subcontracting_operations','rate']

			doc = frappe.get_all(doctype , filters = filters , fields = fields)
			for j in doc:
				if j.item_code:
					unvaried = frappe.get_value('Subcontracting Operations',j.custom_subcontracting_operations , 'unvaried')
					if unvaried :
						item_list.append(j.item_code)

					else:
						bom_exist = frappe.get_value("Outsourcing BOM",j.item_code,'name')
						if bom_exist :
							bom = frappe.get_doc("Outsourcing BOM",j.item_code)
							child_bom = bom.get("outsourcing_bom_details")
							for k in child_bom:
								item_list.append(k.item_code)
								
						else:
							raw_item_code = frappe.get_value("Item",j.item_code,'raw_material')
							if raw_item_code:
								item_list.append(raw_item_code)
							
							else:
								frappe.msgprint(f"There is no 'Raw Material'defined at Item master of Item {j.item_code}")
		return item_list

	@frappe.whitelist()
	def calculating_total(self,child_table ,total_field):
		table = self.get(child_table)
		total = 0
		for i in table:
			field_data = i.get(total_field)
			total = total + getVal(field_data)
		return total
	

	
# =================================================================================================== IN ===================================================================================================
	@frappe.whitelist()
	def set_out_sub_list(self):
		if self.in_or_out == 'IN' and (self.without_order or self.blanket_order or self.purchase_order):
			supplier_id = self.supplier_id
			company = self.company
			if not supplier_id and not company:
				frappe.throw('Please select supplier_id and company')
			else :
				query = """
									SELECT a.name name, b.raw_item_code ,b.production_quantity ,b.production_done_quantity , b.name reference_id , b.subcontracting_operations
									FROM `tabSubcontracting` a
									LEFT JOIN `tabItems Subcontracting` b ON a.name = b.parent
									WHERE a.supplier_id = %s AND a.company = %s AND b.docstatus = 1 AND b.parentfield = 'items_subcontracting' AND b.out_done = 0 AND a.in_or_out = 'Out'
						"""

				paremeters = [supplier_id , company]
				if self.in_entry_type == 'Subcontracting' and self.linking_option and (self.blanket_order or self.purchase_order):
					item_list = self.raw_item_list()
					if item_list :
						paremeters.append(tuple(item_list))
						query += """ AND b.raw_item_code  in %s """

					else:
						pass


				query += """ORDER BY b.raw_item_code """

				data = frappe.db.sql(query,tuple(paremeters),as_dict="True")
				
				for i in data:

					self.append("out_subcontracting_list",
												{	'subcontracting': i.name ,
													'raw_item_code'	: i.raw_item_code ,
													'raw_item_name':ItemName(i.raw_item_code),
													'subcontracting_operations':i.subcontracting_operations,
													'production_out_quantity': getVal(i.production_quantity) ,
													'production_done_quantity':getVal(i.production_done_quantity) ,
													'production_remaining_quantity': getVal(i.production_quantity) - getVal(i.production_done_quantity),
													'reference_id': i.reference_id,
													'weight_per_unit':ItemWeight(i.raw_item_code),
												},),
		self.loan_set_in_list()
			
	@frappe.whitelist()
	def set_out_list_in_finished_item(self):
		if self.in_or_out == 'IN':
			out_subcontracting_list = self.get('out_subcontracting_list' , filters = {'check': True , 'subcontracting_operations' : ['not in',(None,'')]})
			if  out_subcontracting_list:
				for d in out_subcontracting_list:
					unvaried = frappe.get_value('Subcontracting Operations',d.subcontracting_operations , 'unvaried')
					if unvaried :
						self.append("in_finished_item_subcontracting",
											{	
												'in_item_code': d.raw_item_code,
												'in_item_name': ItemName(d.raw_item_code),
												'order_type': d.order_type,
												'select_order': d.select_order,
												'operation': d.subcontracting_operations,
												'target_warehouse' : self.target_warehouse,
												'unvaried': unvaried,
												'weight_per_unit':ItemWeight(d.raw_item_code),
												'rate_from_order': d.rate_from_order,
												'subcontracting': d.subcontracting,
												'remaining_quantity':d.production_remaining_quantity,
											},),
					else:
						# bom_exist = frappe.get_value("Outsourcing BOM",j.in_item_code,'name')
						# if bom_exist :
						# 	pass
							# bom = frappe.get_doc("Outsourcing BOM",j.in_item_code)
							# child_bom = bom.get("outsourcing_bom_details")
							# for k in child_bom:
							# 	self.append("in_raw_item_subcontracting",
							# 				{	'in_item_code': j.in_item_code ,
							# 					'raw_item_code'	: k.item_code,
							# 					'raw_item_name':ItemName(k.item_code),
							# 					'quantity_per_finished_item': k.required_quantity,
							# 					'actual_required_quantity': getVal(j.quantity) * getVal(k.required_quantity),
							# 					'quantity': getVal(j.quantity) * getVal(k.required_quantity),
							# 					'reference_id': j.name,
							# 					'source_warehouse':self.source_warehouse,
							# 					'weight_per_unit':ItemWeight(k.item_code),
							# 					'total_required_weight': ItemWeight(k.item_code) * (getVal(j.quantity) * getVal(k.required_quantity)),
							# 				},),
						# else:
							finish_item_code = frappe.get_value("Item",{'raw_material': d.raw_item_code},'name')
							if finish_item_code:
								self.append("in_finished_item_subcontracting",
											{	
												'in_item_code': finish_item_code,
												'in_item_name': ItemName(finish_item_code),
												'order_type': d.order_type,
												'select_order': d.select_order,
												'operation': d.subcontracting_operations,
												'target_warehouse' : self.target_warehouse,
												'unvaried': unvaried,
												'weight_per_unit':ItemWeight(finish_item_code),
												'rate_from_order': d.rate_from_order,
												'subcontracting': d.subcontracting,
												'remaining_quantity':d.production_remaining_quantity,
											},),
							else:
								frappe.msgprint(f"There is no 'Raw Item '{d.raw_item_code} defined at any Item master")

	
	@frappe.whitelist()
	def loan_set_in_list(self):
		if self.in_or_out == 'IN' and self.in_entry_type == 'Material Loan Given':
			supplier_id = self.supplier_id
			company = self.company
			if not supplier_id and not company:
				frappe.throw('Please select supplier_id and company')
			else :
				query = """
									SELECT a.name name, b.finished_item_code ,b.production_quantity ,b.production_done_quantity , b.name reference_id , b.target_warehouse
									FROM `tabSubcontracting` a
									LEFT JOIN `tabLoan Items Subcontracting` b ON a.name = b.parent
									WHERE a.supplier_id = %s AND a.company = %s AND b.docstatus = 1 AND b.out_done = 0 AND a.out_entry_type = 'Material Loan Given'
						"""

				paremeters = [supplier_id , company]
				query += """ORDER BY b.finished_item_code """

				data = frappe.db.sql(query,tuple(paremeters),as_dict="True")
				# frappe.throw(str(data))
				for i in data:
					self.append("in_loan_items_subcontracting",
												{	'subcontracting': i.name ,
													'finished_item_code': i.finished_item_code ,
													'finished_item_name':ItemName(i.finished_item_code),
													'source_warehouse': i.target_warehouse,
													'target_warehouse': self.target_warehouse,
													'available_quantity': get_available_quantity(i.finished_item_code , i.target_warehouse ) if i.finished_item_code and i.target_warehouse else 0 ,
													'production_done_quantity':getVal(i.production_done_quantity) ,
													'in_able_quantity': getVal(i.production_quantity) - getVal(i.production_done_quantity),
													'reference_id': i.reference_id,
													'weight_per_unit':ItemWeight(i.finished_item_code),
												},),








			
	@frappe.whitelist()
	def set_in_finished_item(self):
		if self.in_entry_type == 'Subcontracting' and self.linking_option and (self.blanket_order or self.purchase_order) :
			if self.linking_option == 'Blanket Order':
				b_o_l = []
				for i in self.blanket_order:
					b_o_l.append(str(i.blanket_order))

				doctype = 'Blanket Order Item'
				filters = {'parent':['in',b_o_l]}
				fields = ['item_code' , 'parent','custom_subcontracting_operations','rate']

			else:
				p_o_l = []
				for j in self.purchase_order:
					p_o_l.append(str(j.purchase_order))

				doctype = 'Purchase Order Item'
				filters = {'parent':['in',p_o_l]}
				fields = ['item_code' , 'parent','custom_subcontracting_operations','rate']

			doc = frappe.get_all(doctype , filters = filters , fields = fields)
			for d in doc:
				self.append("in_finished_item_subcontracting",{
											'in_item_code': d.item_code,
											'in_item_name': ItemName(d.item_code),
											'order_type': self.linking_option,
											'select_order': d.parent,
											'operation': d.custom_subcontracting_operations,
											'target_warehouse' : self.target_warehouse,
											'unvaried': frappe.get_value('Subcontracting Operations',d.custom_subcontracting_operations , 'unvaried') if d.custom_subcontracting_operations else False ,
											'weight_per_unit':ItemWeight(d.item_code),
											'rate_from_order': d.rate,
											},),
	

	@frappe.whitelist()
	def set_raw_order_data(self , table):
		self.set_quantity()
		self.finish_total_quantity_calculate()
		items = self.get(table)
		for j in items:
			if j.in_item_code and j.total_quantity:
				if j.unvaried :
					self.append("in_raw_item_subcontracting",
										{	'in_item_code': j.in_item_code ,
											'raw_item_code'	: j.in_item_code ,
											'raw_item_name':ItemName(j.in_item_code),
											'quantity_per_finished_item':1,
											'actual_required_quantity': getVal(j.quantity),
											'quantity': getVal(j.quantity),
											'reference_id': j.name,
											'source_warehouse':self.source_warehouse,
											'weight_per_unit':ItemWeight(j.in_item_code),
											'total_required_weight': ItemWeight(j.in_item_code) * getVal(j.quantity),
										},),
				else:
					bom_exist = frappe.get_value("Outsourcing BOM",j.in_item_code,'name')
					if bom_exist :
						bom = frappe.get_doc("Outsourcing BOM",j.in_item_code)
						child_bom = bom.get("outsourcing_bom_details")
						for k in child_bom:
							self.append("in_raw_item_subcontracting",
										{	'in_item_code': j.in_item_code ,
											'raw_item_code'	: k.item_code,
											'raw_item_name':ItemName(k.item_code),
											'quantity_per_finished_item': k.required_quantity,
											'actual_required_quantity': getVal(j.quantity) * getVal(k.required_quantity),
											'quantity': getVal(j.quantity) * getVal(k.required_quantity),
											'reference_id': j.name,
											'source_warehouse':self.source_warehouse,
											'weight_per_unit':ItemWeight(k.item_code),
											'total_required_weight': ItemWeight(k.item_code) * (getVal(j.quantity) * getVal(k.required_quantity)),
										},),
					else:
						raw_item_code = frappe.get_value("Item",j.in_item_code,'raw_material')
						if raw_item_code:
							self.append("in_raw_item_subcontracting",
										{	'in_item_code': j.in_item_code ,
											'raw_item_code'	: raw_item_code ,
											'raw_item_name':ItemName(raw_item_code),
											'quantity_per_finished_item':1,
											'actual_required_quantity': getVal(j.quantity),
											'quantity': getVal(j.quantity),
											'reference_id': j.name,
											'source_warehouse':self.source_warehouse,
											'weight_per_unit':ItemWeight(raw_item_code),
											'total_required_weight': ItemWeight(raw_item_code) * getVal(j.quantity),
										},),
						else:
							frappe.msgprint(f"There is no 'Raw Material'defined at Item master of Item {j.in_item_code}")
		self.set_table_data('in_finished_item_subcontracting' , 'target_warehouse' , self.target_warehouse ,)
		self.set_out_subcontracting()
		self.update_bifurcation_out_subcontracting()

		self.calculating_total_in_qty()

	@frappe.whitelist()
	def update_bifurcation_out_subcontracting(self):
		for d in self.get('in_finished_item_subcontracting'):
			if d.subcontracting:
				ok_quantity = getVal(d.quantity)
				as_it_is = getVal(d.as_it_is)
				cr_casting_rejection = getVal(d.cr_casting_rejection)
				mr_machine_rejection = getVal(d.mr_machine_rejection)
				rw_rework = getVal(d.rw_rework)

				total_quantity = as_it_is + cr_casting_rejection + mr_machine_rejection + rw_rework +ok_quantity
				total_value = total_quantity
				reference_item = None
				for j in self.get('in_raw_item_subcontracting',filters={'reference_id': d.reference_id}):
					reference_item = j.raw_item_code


				rows = self.get('bifurcation_out_subcontracting', filters={'subcontracting': d.subcontracting , 'raw_item_code': reference_item})

				remaining_value = total_value
				for r in rows:
					row_capacity = r.production_remaining_quantity
					if remaining_value >= row_capacity:
						
						# Distribute as_it_is, cr_casting_rejection, mr_machine_rejection, rw_rework
						r.ok_quantity = min(ok_quantity, row_capacity)
						ok_quantity -= r.ok_quantity
						r.as_it_is = min(as_it_is, row_capacity)
						as_it_is -= r.as_it_is
						r.cr_quantity = min(cr_casting_rejection, row_capacity)
						cr_casting_rejection -= r.cr_quantity
						r.mr_quantity = min(mr_machine_rejection, row_capacity)
						mr_machine_rejection -= r.mr_quantity
						r.rw_quantity = min(rw_rework, row_capacity)
						rw_rework -= r.rw_quantity

						r.production_quantity = row_capacity

						remaining_value -= row_capacity
					else:
						
						# Distribute remaining as_it_is, cr_casting_rejection, mr_machine_rejection, rw_rework
						r.ok_quantity = min(ok_quantity, remaining_value)
						ok_quantity -= r.ok_quantity
						r.as_it_is_quantity = min(as_it_is, remaining_value)
						as_it_is -= r.as_it_is_quantity
						r.cr_quantity = min(cr_casting_rejection, remaining_value)
						cr_casting_rejection -= r.cr_quantity
						r.mr_quantity = min(mr_machine_rejection, remaining_value)
						mr_machine_rejection -= r.mr_quantity
						r.rw_quantity = min(rw_rework, remaining_value)
						rw_rework -= r.rw_quantity

						r.production_quantity = remaining_value

						remaining_value = 0
						break

				if remaining_value > 0:
					frappe.throw("Not enough capacity in rows to distribute all values.")

	# @frappe.whitelist()
	# def update_bifurcation_out_subcontracting(self):
	# 	for d in self.get('in_finished_item_subcontracting'):
	# 		if d.subcontracting:
	# 			as_it_is = getVal(d.as_it_is)
	# 			cr_casting_rejection = getVal(d.cr_casting_rejection)
	# 			mr_machine_rejection = getVal(d.mr_machine_rejection)
	# 			rw_rework = getVal(d.rw_rework)

	# 			total_quantity = as_it_is + cr_casting_rejection + mr_machine_rejection + rw_rework
	# 			total_value = total_quantity


	# 			rows = self.get('bifurcation_out_subcontracting' , filters={'subcontracting':d.subcontracting})
				
	# 			remaining_value = total_value
	# 			for r in rows:
	# 				row_capacity = r.production_remaining_quantity
	# 				frappe.msgprint(str(r.production_remaining_quantity))
	# 				if remaining_value >= row_capacity:
	# 					frappe.msgprint('if')
	# 					# r.production_quantity = row_capacity
	# 					setattr(r, 'production_quantity', row_capacity)
	# 					remaining_value -= row_capacity
	# 				else:
	# 					frappe.msgprint('else')
	# 					# r.production_quantity = remaining_value
	# 					setattr(r, 'production_quantity', remaining_value)
	# 					remaining_value = 0
	# 					break

	# 			if remaining_value > 0:
	# 				frappe.throw("Not enough capacity in rows to distribute all values.")



	@frappe.whitelist()
	def set_out_subcontracting(self):
		in_raw_item_subcontracting = self.get("in_raw_item_subcontracting")
		raw_item_code_list = []
		supplier_id = self.supplier_id
		company = self.company
		if not supplier_id and not company:
			frappe.throw('Please select supplier_id and company')
		for d in in_raw_item_subcontracting:
			raw_item_code_list.append(str(d.raw_item_code))
		data = frappe.db.sql("""
							SELECT a.name name, b.raw_item_code ,b.production_quantity ,b.production_done_quantity , b.name reference_id
							FROM `tabSubcontracting` a
							LEFT JOIN `tabItems Subcontracting` b ON a.name = b.parent
							WHERE b.raw_item_code IN %s AND a.supplier_id = %s AND a.company = %s AND b.docstatus = 1 AND b.out_done = 0 AND b.parentfield = 'items_subcontracting'
					   		ORDER BY b.raw_item_code
						""",(tuple(raw_item_code_list+['xxxxxx']) ,supplier_id ,company),as_dict="True")
		for i in data:
			self.append("bifurcation_out_subcontracting",
										{	'subcontracting': i.name ,
											'raw_item_code'	: i.raw_item_code ,
											'raw_item_name':ItemName(i.raw_item_code),
											'production_out_quantity': getVal(i.production_quantity) ,
											'production_done_quantity':getVal(i.production_done_quantity) ,
											'production_remaining_quantity': getVal(i.production_quantity) - getVal(i.production_done_quantity),
											'reference_id': i.reference_id,
											'weight_per_unit':ItemWeight(i.raw_item_code),
										},),
		out_subcontracting_list = self.get('out_subcontracting_list', filters = {'check': True})
		if 	out_subcontracting_list:
			for p in out_subcontracting_list:
				for q in self.get('bifurcation_out_subcontracting', filters = {'reference_id': p.reference_id}):
					q.check = True

	@frappe.whitelist()
	def set_quantity(self):
		in_finished_item_subcontracting = self.get('in_finished_item_subcontracting')
		for i in in_finished_item_subcontracting:
			if not i.reference_id:
				i.reference_id = i.name
			for j in self.get("in_raw_item_subcontracting" , filters = {'reference_id':i.reference_id}):
				actual_required_quantity = getVal(j.quantity_per_finished_item) * getVal(i.quantity)
				j.actual_required_quantity = actual_required_quantity
				j.quantity = actual_required_quantity

		self.finish_total_quantity_calculate()


	@frappe.whitelist()
	def rejected_item(self):
		exists = frappe.db.exists('Subcontracting Setting',self.company)
		c = m = r = a = None
		if exists:
			doc =  frappe.get_doc('Subcontracting Setting',self.company)
			c = doc.cr_warehouse
			m = doc.mr_warehouse
			r = doc.rw_warehouse
			a = doc.as_it_is_warehouse


		self.set_quantity()
		in_finished =  self.get('in_finished_item_subcontracting')
		for i in in_finished :
			in_raw = self.get('in_raw_item_subcontracting' , filters = {'reference_id': i.reference_id,})
			for j in in_raw :
				as_it_is = getVal(j.quantity_per_finished_item) * getVal(i.as_it_is)
				cr_casting_rejection = getVal(j.quantity_per_finished_item) * getVal(i.cr_casting_rejection)
				mr_machine_rejection = getVal(j.quantity_per_finished_item) * getVal(i.mr_machine_rejection)
				rw_rework = getVal(j.quantity_per_finished_item) * getVal(i.rw_rework)
				if as_it_is:
					self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': i.in_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': as_it_is,
								'rejection_type' :'AS IT IS (AS IT AS)' ,
								'source_warehouse':j.source_warehouse,
								'target_warehouse':a ,
								'reference_id':i.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
								'total_rejected_weight': ItemWeight(j.raw_item_code) * as_it_is,
							},),
				if cr_casting_rejection:
					self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': i.in_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': cr_casting_rejection,
								'rejection_type' :'CR (Casting Rejection)' ,
								'source_warehouse': j.source_warehouse,
								'target_warehouse':c ,
								'reference_id':i.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
								'total_rejected_weight': ItemWeight(j.raw_item_code) * cr_casting_rejection,
							},),
				if mr_machine_rejection:
					self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': i.in_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': mr_machine_rejection,
								'rejection_type' :'MR (Machine Rejection)' ,
								'source_warehouse': j.source_warehouse,
								'target_warehouse':m ,
								'reference_id':i.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
								'total_rejected_weight': ItemWeight(j.raw_item_code) * mr_machine_rejection,
							},),
				if rw_rework:
					self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': i.in_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': rw_rework,
								'rejection_type' :'RW (Rework)' ,
								'source_warehouse':j.source_warehouse,
								'target_warehouse':r ,
								'reference_id':i.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
								'total_rejected_weight': ItemWeight(j.raw_item_code) * rw_rework,
							},),

	@frappe.whitelist()
	def finish_total_quantity_calculate(self):
		for j in self.get("in_finished_item_subcontracting"):
			j.total_quantity = getVal(j.quantity) + getVal(j.cr_casting_rejection) + getVal(j.mr_machine_rejection) + getVal(j.rw_rework) + getVal(j.as_it_is)
			j.total_finished_weight =  j.total_quantity * getVal(j.weight_per_unit)
			j.total_amount = getVal(j.quantity) * getVal(j.rate_from_order)

	@frappe.whitelist()
	def bifurgation_quantity_calculate(self):
		for j in self.get("bifurcation_out_subcontracting"):
			j.production_quantity = getVal(j.ok_quantity) + getVal(j.cr_quantity) + getVal(j.mr_quantity) + getVal(j.rw_quantity) + getVal(j.as_it_is_quantity)
			j.total_finished_weight =  j.production_quantity * getVal(j.weight_per_unit)
			# j.total_amount = j.total_quantity * getVal(j.rate_from_order)


	@frappe.whitelist()
	def validate_entry(self):
		result_dict = {}
		out_raw_dict = {}

		raw_data = self.get("in_raw_item_subcontracting")
		if not raw_data:
			frappe.throw("'In Raw Item Subcontrating' table is mandatory when you are inwording the items there is no data in table this happends due to slow network or any server problem, just repeat the process one more time")

		for j in self.get("in_raw_item_subcontracting"):
			raw_item_code, quantity = j.raw_item_code, j.quantity

			if raw_item_code not in result_dict:
				result_dict[raw_item_code] = [0, 0]

			result_dict[raw_item_code][0] += quantity
			result_dict[raw_item_code][1] = max(quantity, result_dict[raw_item_code][1])

		for k in self.get("in_rejected_items_reasons_subcontracting"):
			raw_item_code, quantity = k.raw_item_code, k.quantity

			if raw_item_code not in result_dict:
				result_dict[raw_item_code] = [0, 0]

			result_dict[raw_item_code][0] += quantity
			result_dict[raw_item_code][1] = max(quantity, result_dict[raw_item_code][1])

		for l in self.get("bifurcation_out_subcontracting"):
			raw_item_code , quantity = l.raw_item_code , l.production_quantity
			out_raw_dict[raw_item_code] = out_raw_dict.get(raw_item_code, 0) + quantity



		for item, qty_range in result_dict.items():
			max_qty ,min_qty = qty_range
			b_qty = out_raw_dict.get(item, None)

			if b_qty is not None and not (min_qty <= b_qty <= max_qty):
				frappe.throw(f"The Quantity for Raw Item '{item}' is should not be more than {max_qty} and should not be less than {min_qty}")
			if b_qty is None:
				frappe.throw(f"You Can Not Inword {item} As It Have Not Any Out Entry")


	@frappe.whitelist()
	def set_source_warehouse(self):
		self.set_table_data('in_raw_item_subcontracting','source_warehouse',self.source_warehouse,'available_quantity','raw_item_code','source_warehouse')
		self.set_table_data('in_rejected_items_reasons_subcontracting','source_warehouse', self.source_warehouse,'available_quantity','raw_item_code','source_warehouse')




	@frappe.whitelist()
	def validate_bifurcation_out_subcontracting(self):
		for i in self.get('bifurcation_out_subcontracting'):
			if i.production_remaining_quantity < i.production_quantity:
				frappe.msgprint("You Can Not Set 'Production Quantity' More Than 'Production Remaining Quantity'")
				i.production_quantity = 0

	@frappe.whitelist()
	def update_get_rejections(self):
		in_finished =  self.get('in_finished_item_subcontracting')
		for i in in_finished :
			as_it_is = 0
			for j in self.get('in_rejected_items_reasons_subcontracting', filters = {'reference_id': i.reference_id , 'rejection_type': 'AS IT IS (AS IT AS)'}):
				as_it_is = as_it_is + j.quantity
			
			if i.as_it_is > as_it_is:
				self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': j.finished_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': i.as_it_is - as_it_is ,
								'rejection_type' : 'AS IT IS (AS IT AS)' ,
								'source_warehouse': j.source_warehouse,
								'reference_id':j.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
							},),


			cr_casting_rejection = 0
			for j in self.get('in_rejected_items_reasons_subcontracting', filters = {'reference_id': i.reference_id , 'rejection_type': 'CR (Casting Rejection)'}):
				cr_casting_rejection = cr_casting_rejection + j.quantity
			
			if i.cr_casting_rejection > cr_casting_rejection:
				self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': j.finished_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': i.cr_casting_rejection - cr_casting_rejection ,
								'rejection_type' : 'CR (Casting Rejection)' ,
								'source_warehouse': j.source_warehouse,
								'reference_id':j.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
							},),

			mr_machine_rejection = 0
			for j in self.get('in_rejected_items_reasons_subcontracting', filters = {'reference_id': i.reference_id , 'rejection_type': 'MR (Machine Rejection)'}):
				mr_machine_rejection = mr_machine_rejection + j.quantity
			
			if i.mr_machine_rejection > mr_machine_rejection:
				self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': j.finished_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': i.mr_machine_rejection - mr_machine_rejection ,
								'rejection_type' : 'MR (Machine Rejection)' ,
								'source_warehouse': j.source_warehouse,
								'reference_id':j.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
							},),

			rw_rework = 0
			for j in self.get('in_rejected_items_reasons_subcontracting', filters = {'reference_id': i.reference_id , 'rejection_type': 'RW (Rework)'}):
				rw_rework = rw_rework + j.quantity
			
			if i.rw_rework > rw_rework:
				self.append("in_rejected_items_reasons_subcontracting",{
								'finished_item_code': j.finished_item_code,
								'raw_item_code': j.raw_item_code,
								'raw_item_name': ItemName(j.raw_item_code),
								'quantity': i.rw_rework - rw_rework ,
								'rejection_type' : 'RW (Rework)' ,
								'source_warehouse': j.source_warehouse,
								'reference_id':j.reference_id,
								'weight_per_unit':ItemWeight(j.raw_item_code),
							},),




	@frappe.whitelist()
	def manifacturing_stock_entry(self):
		if self.in_or_out == 'IN':
			default_expense_account = frappe.get_value('Subcontracting Setting',self.company ,'default_expense_account')
			in_finished =  self.get('in_finished_item_subcontracting' , filters = {'quantity': ['not in',(None,0)]})
			for i in in_finished :
				se = frappe.new_doc("Stock Entry")
				se.stock_entry_type = "Manufacture"
				se.company = self.company
				se.set_posting_time = True
				se.posting_date = self.posting_date
				in_raw = None
				in_raw = self.get('in_raw_item_subcontracting' , filters = {'reference_id': i.reference_id })
				for j in in_raw :
					se.append(
						"items",
						{
							"item_code": j.raw_item_code,
							"qty":  j.quantity,
							"s_warehouse": j.source_warehouse,
						},)
					
				if in_raw :
					se.append(
						"items",
						{
							"item_code": i.in_item_code,
							"qty": i.quantity,
							"t_warehouse": i.target_warehouse,
							"is_finished_item": True
						},)

				if i.total_amount and default_expense_account:
					se.append(
								"additional_costs",
								{
									"expense_account":default_expense_account,
									"description": str(i.operation),
									"amount": i.total_amount ,

								},)

				se.custom_subcontracting = self.name
				if se.items:		
					se.insert()
					se.save()
					se.submit()



	@frappe.whitelist()
	def calculating_total_in_qty(self):
		self.total_in_qty = self.calculating_total('in_finished_item_subcontracting','total_quantity')
		self.total_in_ok_qty = self.calculating_total('in_finished_item_subcontracting','total_in_ok_qty')
		self.total_in_as_it_is_qty = self.calculating_total('in_finished_item_subcontracting','total_in_as_it_is_qty')
		self.total_in_cr_qty = self.calculating_total('in_finished_item_subcontracting','total_in_cr_qty')
		self.total_in_mr_qty = self.calculating_total('in_finished_item_subcontracting','total_in_mr_qty')
		self.total_in_rw_qty = self.calculating_total('in_finished_item_subcontracting','total_in_rw_qty')


	@frappe.whitelist()
	def update_out_entry(self):
		for i in self.get('bifurcation_out_subcontracting'):
			doc = frappe.get_doc('Items Subcontracting',i.reference_id)
			production_done_quantity = doc.production_done_quantity
			updated_value = getVal(production_done_quantity) + getVal(i.production_quantity)
			doc.production_done_quantity = updated_value
			if doc.production_quantity < doc.production_done_quantity :
				frappe.throw(str('production_done_quantity is should not be greater than production_quantity'))
				
			if doc.production_done_quantity == doc.production_quantity:
				doc.out_done = True
			doc.save()


	@frappe.whitelist()
	def loan_update_out_entry(self):
		for i in self.get('in_loan_items_subcontracting'):
			doc = frappe.get_doc('Loan Items Subcontracting',i.reference_id)
			production_done_quantity = doc.production_done_quantity
			updated_value = getVal(production_done_quantity) + getVal(i.in_quantity)
			doc.production_done_quantity = updated_value
			if doc.production_quantity < doc.production_done_quantity :
				frappe.throw(str('production_done_quantity is should not be greater than production_quantity'))
			if doc.production_done_quantity == doc.production_quantity:
				doc.out_done = True
			doc.save()
	
	@frappe.whitelist()
	def cancel_update_out_entry(self):
		for i in self.get('bifurcation_out_subcontracting'):
			doc = frappe.get_doc('Items Subcontracting',i.reference_id)
			production_done_quantity = doc.production_done_quantity
			updated_value = getVal(production_done_quantity) - getVal(i.production_quantity)
			doc.production_done_quantity = updated_value
			if doc.production_done_quantity == doc.production_quantity:
				doc.out_done = True
			else:
				doc.out_done = False
			doc.save()

	@frappe.whitelist()
	def loan_cancel_update_out_entry(self):
		for i in self.get('in_loan_items_subcontracting'):
			doc = frappe.get_doc('Loan Items Subcontracting',i.reference_id)
			production_done_quantity = doc.production_done_quantity
			updated_value = getVal(production_done_quantity) - getVal(i.in_quantity)
			doc.production_done_quantity = updated_value
			if doc.production_done_quantity == doc.production_quantity:
				doc.out_done = True
			else:
				doc.out_done = False
			doc.save()

# =================================================================================================== IN ===================================================================================================

	@frappe.whitelist()
	def update_value(self):
		self.customer_name = self.supplier_name
		self.customer_address = self.supplier_address

		comp_state = frappe.get_value("Address", {"address_title": self.company}, 'state')
		supp_state = frappe.get_value("Address", {"address_title": self.supplier_id}, 'state')

		tot_taxable_amount = 0
		tot_amount = 0
		tot_weight = 0
		tot_prod_qty = 0
		subcontracting_set_rate = frappe.get_value("Subcontracting Setting", {'name': self.company}, 'rate_for_print')


		for i in self.items_subcontracting:
			item_doc = frappe.get_doc("Item", {'name':i.raw_item_code})
			i.description = item_doc.item_name if i.description is None else i.description
			i.gst_hsn_code = item_doc.gst_hsn_code

			if item_doc.custom_production_uom_definition:
				for prod_uom in item_doc.custom_production_uom_definition:
					i.uom = prod_uom.uom
					i.weight_per_unit = prod_uom.value_per_unit
			else:
				i.weight_per_unit = 0
				frappe.msgprint("UOM And Value Per Unit Should be defined in Item Master")

			i.total_finished_weight = i.production_quantity * i.weight_per_unit

			i.rate = subcontracting_set_rate
			i.amount = i.production_quantity * subcontracting_set_rate
			tot_prod_qty += i.production_quantity

			tot_amount += i.amount
			tot_weight += i.total_finished_weight

			tax_rate = frappe.get_value("Item Tax Template", {'name':item_doc.taxes[0].item_tax_template}, 'gst_rate')
			if comp_state == supp_state:
				i.cgst_rate = i.sgst_rate = (tax_rate/2)
				i.cgst_amount = i.sgst_amount = round((i.amount/100)*(i.cgst_rate),2)
				i.taxable_value = i.cgst_amount + i.sgst_amount
				tot_taxable_amount += i.taxable_value
			else:
				i.igst_rate = tax_rate
				i.igst_amount = round((i.amount/100)*(i.igst_rate),2)
				i.taxable_value = i.igst_amount
				tot_taxable_amount += i.taxable_value

		self.total_production_qty = tot_prod_qty

		if comp_state == supp_state:
			filter ={'is_inter_state': 0, 'is_reverse_charge': 0,'gst_state': comp_state}
			tot_taxable_amount = tot_taxable_amount/2
		else:
			filter ={'is_inter_state': 1, 'is_reverse_charge': 0,'gst_state': comp_state}

		tax_cat_list = frappe.get_value("Tax Category",filter,'name')
		
		self.taxes_and_charges = frappe.get_value("Sales Taxes and Charges Template", {'tax_category': tax_cat_list, 'company': self.company}, 'name')
		if self.taxes_and_charges == None:
			frappe.msgprint("Template Not Found")
		else:
			taxes_charges_doc = frappe.get_doc("Sales Taxes and Charges Template",{'name':self.taxes_and_charges})
			for tx in taxes_charges_doc.taxes:
				tot_amount += tot_taxable_amount
				self.append("taxes",{
					"charge_type": tx.charge_type,
					"account_head": tx.account_head,
					"description": tx.description,
					"cost_center": tx.cost_center,
					"tax_amount": tot_taxable_amount,
					"total": round(tot_amount,2)
				})
				
		self.total_amount = tot_amount
		self.total_weight = tot_weight
		self.rounded_total = round(tot_amount)

		for i in range(len(self.items_subcontracting)):
			item_doc = frappe.get_doc("Items Subcontracting", self.items_subcontracting[i])
			self.append("items",{
				"raw_item_code": item_doc.raw_item_code,
				"raw_item_name": item_doc.raw_item_name,
				"target_warehouse": item_doc.target_warehouse,
				"source_warehouse": item_doc.source_warehouse,
				"available_quantity": item_doc.available_quantity,
				"description": item_doc.description,
				"gst_hsn_code": item_doc.gst_hsn_code,
				"stock_uom": item_doc.stock_uom,
				"production_quantity": item_doc.production_quantity,
				"amount": item_doc.amount,
				"uom": item_doc.uom,
				"rate": item_doc.rate,
				"weight_per_unit": item_doc.weight_per_unit,
				"total_finished_weight": item_doc.total_finished_weight,
				"rate_for_print": item_doc.rate_for_print,
				"production_done_quantity": item_doc.production_done_quantity,
				"igst_rate": item_doc.igst_rate,
				"cgst_rate": item_doc.cgst_rate,
				"sgst_rate": item_doc.sgst_rate,
				"cess_rate": item_doc.cess_rate,
				"cess_non_advol_rate": item_doc.cess_non_advol_rate,
				"igst_amont": item_doc.igst_amount,
				"cgst_amont": item_doc.cgst_amount,
				"sgst_amont": item_doc.sgst_amount,
				"cess_amont": item_doc.cess_amount,
				"cess_non_advol_amont": item_doc.cess_non_advol_amount,
				"taxable_value": item_doc.taxable_value,
				"item_name": item_doc.item_name,
				"item_code": item_doc.item_code,
				"qty": item_doc.total_finished_weight
				})

	@frappe.whitelist()
	def update_warehouse(self):
		if self.supplier_id:
			data = frappe.get_doc("Supplier",self.supplier_id)
			if self.in_or_out == 'OUT':
				if self.source_warehouse:
					self.source_warehouse = None
				self.target_warehouse = data.custom_subcontracting_warehouse
			if self.in_or_out == 'IN':
				if self.target_warehouse:
					self.target_warehouse = None
				self.source_warehouse = data.custom_subcontracting_warehouse
		else:
			frappe.throw("No Supplier ID")

	@frappe.whitelist()
	def update_company_address(self):
		if self.company:
			comp_add_data = frappe.get_doc("Address", {"address_title": self.company})
			self.company_address = comp_add_data.name
			self.company_gstin = comp_add_data.gstin
			self.comp_address = f"{comp_add_data.address_line1}\n{comp_add_data.address_line2}\n{comp_add_data.city}\n{comp_add_data.state}\n{comp_add_data.country}"
			self.shipping_address_name = comp_add_data.name
		else:
			frappe.throw("No Company Selected")

	@frappe.whitelist()
	def update_supplier_address(self):
		if self.supplier_id:
			comp_add_data = frappe.get_doc("Address", {"address_title": self.supplier_name})
			self.supplier_address = comp_add_data.name
			self.supplier_gstin = comp_add_data.gstin
			self.sup_address = f"{comp_add_data.address_line1}\n{comp_add_data.address_line2}\n{comp_add_data.city}\n{comp_add_data.state}\n{comp_add_data.country}"
			self.dispatch_address_name = comp_add_data.name
			self.gst_category = comp_add_data.gst_category

			sup_data = frappe.get_doc("Supplier",self.supplier_id)
			if sup_data.is_transporter == 1:
				self.transporter = self.supplier_id
				self.transporter_name = self.supplier_name
				self.gst_transporter_id = sup_data.gst_transporter_id

			self.place_of_supply = f"{comp_add_data.gst_state_number} - {comp_add_data.gst_state}"
			self.update_warehouse()
		else:
			frappe.throw("No Supplier Selected")

	def update_raw_list(self, child_table, field):
		for i in self.get(child_table, filters={field:0}):
			self.get(child_table).remove(i)

	def set_foundry_rejection_analysis(self):
		if self.in_or_out == 'IN':
			data = self.get('in_rejected_items_reasons_subcontracting')
			if not data:
				self.custom_foundry_rejection_analaysis = 1