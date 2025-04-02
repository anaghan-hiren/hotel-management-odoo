# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from datetime import datetime, date 

class HotelFolio(models.Model):
	_inherit = "hotel.folio"
	_order = "reservation_id desc"

	reservation_id = fields.Many2one(
		"hotel.reservation", "Reservation", ondelete="restrict"
	)
	checkin = fields.Datetime('Expected-Date-Arrival', related='reservation_id.checkin')
	checkout = fields.Datetime("Expected-Date-Departure", related='reservation_id.checkout')
	price_subtotal = fields.Monetary("Subtotal", compute='_get_folio_subtotal')
	type_of_rate = fields.Selection(related='reservation_id.type_of_rate')
	is_show_register_payment = fields.Boolean('Is Register Payment',compute="compute_on_register_payment")
	blocking_line = fields.Many2one('split.reservation.line','blocking')
	room_close_id = fields.Many2one('hotel.room','Room For Close Day')

	service_line_ids = fields.One2many(
		"hotel.service.line",
		"folio_id",
		readonly=True,
		states={"draft": [("readonly", False)], "sent": [("readonly", False)], "sale": [("readonly", False)]},
		help="Hotel services details provided to"
			 "Customer and it will included in "
			 "the main Invoice.",
	)

	rooms_lines_total = fields.Float("Total Amount (Rooms)",compute="compute_on_rooms_lines")
	service_lines_total = fields.Float("Total Amount (Services)" ,compute="compute_on_rooms_lines")
	service_lines_tax = fields.Float("Total Amount Tax (Services)", compute="compute_on_rooms_lines")
	grand_total = fields.Float('Grand Total')
	filter_service_lines_total = fields.Float("Total Amount (Services) :",compute="compute_on_rooms_lines_filter")
	filter_service_lines_tax = fields.Float("Total Amount Tax (Services) :",compute="compute_on_rooms_lines_filter")
	filter_amount_untaxed = fields.Float("Untaxed Amount :",compute="compute_on_rooms_lines_filter")
	filter_amount_tax = fields.Float("Taxes :",compute="compute_on_rooms_lines_filter")	
	filter_amount_total = fields.Float("Grand Total :",compute="compute_on_rooms_lines_filter")	
	filter_rooms_lines_total = fields.Float("Total Amount (Rooms) :",compute="compute_on_rooms_lines_filter")
	is_main_guest_use = fields.Boolean("Is Main Guest Use")
	room_person_ids = fields.Many2many("split.reservation.guest.name","rel_folio_s_line_room","folio_line_id","folio_id",string="Guest Name")
	avl_room_person_ids = fields.Many2many("split.reservation.guest.name","rel_folio_a_line_room","folio_a_line_id","folio_a_id",string="Available Guest Name",compute="compute_on_avl_room_person_ids")

	def compute_on_avl_room_person_ids(self):
		for rec in self:
			rec.avl_room_person_ids = rec.blocking_line.geust_lines

	@api.depends()
	def compute_on_rooms_lines(self):
		for rec in self:
			rooms_lines_total = 0
			service_lines_total = 0
			service_lines_tax = 0
			for room_line in rec.room_line_ids:
				subtotal_room = room_line.product_uom_qty * room_line.price_unit
				rooms_lines_total += subtotal_room
			for service_line in rec.service_line_ids:
				subtotal_service = service_line.product_uom_qty * service_line.price_unit
				service_lines_total += subtotal_service
				taxes = service_line.tax_id.compute_all(service_line.price_unit, rec.currency_id, service_line.product_uom_qty, product=service_line.product_id, partner=rec.partner_shipping_id)
				service_lines_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
			rec.rooms_lines_total = rooms_lines_total
			rec.service_lines_total = service_lines_total
			rec.service_lines_tax = service_lines_tax

	@api.depends('service_line_ids','is_main_guest_use','room_person_ids')
	def compute_on_rooms_lines_filter(self):
		for rec in self:
			service_line_ids = []
			if rec.is_main_guest_use:
				service_line_ids += rec.service_line_ids.filtered(lambda x:x.is_main_guest_use).ids
			if rec.room_person_ids:
				geusts = rec.room_person_ids.ids
				service_line_ids += rec.service_line_ids.filtered(lambda x:any(x.room_person_ids.filtered(lambda y:y._origin.id in geusts))).ids
			rooms_lines_total = 0
			service_lines_total = 0
			service_lines_tax = 0
			service_line_ids = rec.service_line_ids.filtered(lambda x:x.id in service_line_ids or x._origin.id in service_line_ids)
			for room_line in rec.room_line_ids:
				subtotal_room = room_line.product_uom_qty * room_line.price_unit
				rooms_lines_total += subtotal_room
			for service_line in service_line_ids:
				subtotal_service = service_line.product_uom_qty * service_line.price_unit
				service_lines_total += subtotal_service
				taxes = service_line.tax_id.compute_all(service_line.price_unit, rec.currency_id, service_line.product_uom_qty, product=service_line.product_id, partner=rec.partner_shipping_id)
				service_lines_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
			rec.filter_rooms_lines_total = rooms_lines_total
			rec.filter_service_lines_total = service_lines_total
			rec.filter_service_lines_tax = service_lines_tax
			rec.filter_amount_untaxed = service_lines_total
			rec.filter_amount_tax = service_lines_tax
			rec.filter_amount_total = service_lines_tax + service_lines_total

	def get_totals(self,is_main_guest_use,geusts,service_payment_type=False):
		for rec in self:
			service_lines_total = 0
			service_lines_tax = 0
			service_line_ids = rec.service_line_ids
			if is_main_guest_use:
				if service_payment_type == "my_services":
					service_line_ids = service_line_ids.filtered(lambda x:x.is_main_guest_use)
			if geusts and not is_main_guest_use:
				service_line_ids = service_line_ids.filtered(lambda x:any(x.room_person_ids.filtered(lambda y:y.id in geusts)))

			for service_line in service_line_ids:
				subtotal_service = service_line.product_uom_qty * service_line.price_unit
				service_lines_total += subtotal_service
				taxes = service_line.tax_id.compute_all(service_line.price_unit, rec.currency_id, service_line.product_uom_qty, product=service_line.product_id, partner=rec.partner_shipping_id)
				service_lines_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))

			if is_main_guest_use and not geusts:
				return service_lines_total + service_lines_tax + rec.rooms_lines_total
			elif not is_main_guest_use and not geusts:
				return service_lines_total + service_lines_tax + rec.rooms_lines_total
			else:
				return service_lines_total + service_lines_tax

	def compute_on_register_payment(self):
		for rec in self:
			if rec.hotel_invoice_id and rec.hotel_invoice_id.state == 'posted' and rec.hotel_invoice_id.amount_residual:
				rec.is_show_register_payment = True
			else:
				rec.is_show_register_payment = False

	def action_draft(self):
		self.write({"state": "draft"})

	def action_cancel(self):
		"""
		@param self: object pointer
		"""
		for rec in self:

			for product in rec.room_line_ids.filtered(
				lambda l: l.order_line.product_id == product
			):
				rooms = self.env["hotel.room"].search([("product_id", "=", product.id)])
				rooms.write({"isroom": True, "status": "available"})
			rec.invoice_ids.button_cancel()
			return rec.order_id.action_cancel()

	@api.depends('room_line_ids')
	def _get_folio_subtotal(self):
		subtotal = 0
		for record in self.room_line_ids:
			if record.price_unit:
				subtotal += record.price_unit
		self.price_subtotal = subtotal

	def write(self, vals):
		res = super(HotelFolio, self).write(vals)
		reservation_line_obj = self.env["hotel.room.reservation.line"]
		for folio in self:
			reservations = reservation_line_obj.search(
				[("reservation_id", "=", folio.reservation_id.id)]
			)
			if len(reservations) == 1:
				for line in folio.reservation_id.reservation_line:
					for room in line.reserve:
						vals = {
							"room_id": room.id,
							"check_in": folio.checkin_date,
							"check_out": folio.checkout_date,
							"state": "assigned",
							"reservation_id": folio.reservation_id.id,
						}
						reservations.write(vals)
		return res

	def action_register_payment(self):
		# for rec in self:
		#     if rec.hotel_invoice_id:
		#         return rec.hotel_invoice_id.action_register_payment()
		if self.reservation_id:
			journal_id = self.env['account.journal'].search([('type','=','bank')], limit=1)
			return {
				'name': _('Register Payment'),
				'res_model': 'account.payment',
				'view_mode': 'form',
				'context': {
					'default_ref': self.reservation_id.reservation_no,
					'default_partner_id':self.reservation_id.partner_id.id,
					'default_journal_id':journal_id.id if journal_id else False,
					'default_reservation_id':self.reservation_id.id,
					'default_folio_id':self.id,
					'default_hotel_payment_type':"room_payment",
					'default_is_show_options':True,
				},
				'target': 'new',
				'view_id': self.env.ref('hotel_reservation.hotel_account_payment_form').id,
				'type': 'ir.actions.act_window',
			}

	def action_transfer_room(self):
		pass

	def action_print_service_line(self):
		return {
			'name': _('Print Service'),
			'res_model': 'print.service',
			'view_mode': 'form',
			'context': {
				'default_avl_room_person_ids':self.blocking_line.geust_lines.ids,
				'default_folio_id':self.id,
			},
			'target': 'new',
			'type': 'ir.actions.act_window',
		}	

class HotelFolioLine(models.Model):
	_inherit = "hotel.folio.line"

	@api.onchange("checkin_date", "checkout_date")
	def _onchange_checkin_checkout_dates(self):
		res = super(HotelFolioLine, self)._onchange_checkin_checkout_dates()
		avail_prod_ids = []
		for room in self.env["hotel.room"].search([]):
			assigned = False
			for line in room.room_reservation_line_ids.filtered(
					lambda l: l.status != "cancel"
			):
				if self.checkin_date and line.check_in and self.checkout_date:
					if (self.checkin_date <= line.check_in <= self.checkout_date) or (
							self.checkin_date <= line.check_out <= self.checkout_date
					):
						assigned = True
					elif (line.check_in <= self.checkin_date <= line.check_out) or (
							line.check_in <= self.checkout_date <= line.check_out
					):
						assigned = True
			if not assigned:
				avail_prod_ids.append(room.product_id.id)
		return res

	def write(self, vals):
		"""
		Overrides orm write method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		Update Hotel Room Reservation line history"""
		reservation_line_obj = self.env["hotel.room.reservation.line"]
		room_obj = self.env["hotel.room"]
		prod_id = vals.get("product_id") or self.product_id.id
		checkin = vals.get("checkin_date") or self.checkin_date
		checkout = vals.get("checkout_date") or self.checkout_date

		is_reserved = self.is_reserved
		if prod_id and is_reserved:
			prod_room = room_obj.search([("product_id", "=", prod_id)], limit=1)
			if self.product_id and self.checkin_date and self.checkout_date:
				old_prod_room = room_obj.search(
					[("product_id", "=", self.product_id.id)], limit=1
				)
				if prod_room and old_prod_room:
					# Check for existing room lines.
					rm_lines = reservation_line_obj.search(
						[
							("room_id", "=", old_prod_room.id),
							("check_in", "=", self.checkin_date),
							("check_out", "=", self.checkout_date),
						]
					)
					if rm_lines:
						rm_line_vals = {
							"room_id": prod_room.id,
							"check_in": checkin,
							"check_out": checkout,
						}
						rm_lines.write(rm_line_vals)
		return super(HotelFolioLine, self).write(vals)


class HotelServiceLine(models.Model):
	_inherit = "hotel.service.line"

	s_date = fields.Date('Date',default=date.today())
	is_main_guest_use = fields.Boolean("Is Main Guest Use")
	room_person_ids = fields.Many2many("split.reservation.guest.name","rel_hotel_s_line_room","hotel_line_id","person_id",string="Guest Name")
	avl_room_person_ids = fields.Many2many("split.reservation.guest.name","rel_hotel_a_line_room","hotel_a_line_id","person_a_id",string="Available Guest Name",compute="compute_on_avl_room_person_ids")

	@api.onchange("is_main_guest_use")
	def onchange_on_room_person_ids(self):
		for rec in self:
			rec.room_person_ids = False

	@api.depends("is_main_guest_use")
	def compute_on_avl_room_person_ids(self):
		for rec in self:
			if rec.is_main_guest_use:
				rec.avl_room_person_ids = []
			else:
				rec.avl_room_person_ids = rec.folio_id.blocking_line.geust_lines

	@api.model
	def default_get(self, fields):
		res = super(HotelServiceLine, self).default_get(fields)
		res.update({"product_uom_qty":1})
		return res

	reservation_id = fields.Many2one("hotel.reservation", "Hotel Reservation")

	@api.onchange("product_id")
	def on_change_product(self):
		for rec in self:
			rec.price_unit = rec.product_id.lst_price