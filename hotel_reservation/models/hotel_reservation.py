# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta, date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import datetime


class HotelReservation(models.Model):
	_name = "hotel.reservation"
	_rec_name = "reservation_no"
	_description = "Reservation"
	_order = "reservation_no desc"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	# Schedual Action function
	@api.model
	def update_state(self):
		self.search([
			('state', '=', 'draft'),
			('option_date', '<', fields.Date.to_string(date.today())),
		]).write({
			'state': 'cancel'
		})

	def _compute_folio_count(self):
		for res in self:
			res.update({"no_of_folio": len(res.folio_id.ids)})

	reservation_no = fields.Char(readonly=True, copy=False)
	date_order = fields.Datetime(
		"Date Ordered",
		readonly=True,
		required=True,
		index=True,
		default=lambda self: fields.Datetime.now(),
	)
	option_date = fields.Date(string='Option Date')

	company_id = fields.Many2one(
		"res.company",
		"Hotel",
		readonly=True,
		index=True,
		required=True,
		default=1,
		states={"draft": [("readonly", False)]},
	)
	individual_company = fields.Selection([
		('person', 'Individual'),
		('company', 'Company'),
	], default='person', widget='radio')

	partner_id = fields.Many2one(
		"res.partner",
		"Guest Name",
		readonly=True,
		index=True,
		required=True,
		states={"draft": [("readonly", False)]},
		# compute='_compute_available_partner_ids', store=False,
	)

	pricelist_id = fields.Many2one(
		"product.pricelist",
		"Rate Code",
		required=True,
		readonly=True,
		states={"draft": [("readonly", False)]},
		help="Pricelist for current reservation.",
	)
	partner_invoice_id = fields.Many2one(
		"res.partner",
		"Invoice Address",
		readonly=True,
		states={"draft": [("readonly", False)]},
		help="Invoice address for " "current reservation.",
	)
	partner_order_id = fields.Many2one(
		"res.partner",
		"Ordering Contact",
		readonly=True,
		states={"draft": [("readonly", False)]},
		help="The name and address of the "
			 "contact that requested the order "
			 "or quotation.",
	)
	partner_shipping_id = fields.Many2one(
		"res.partner",
		"Delivery Address",
		readonly=True,
		states={"draft": [("readonly", False)]},
		help="Delivery address" "for current reservation. ",
	)
	checkin = fields.Datetime(
		"Expected-Date-Arrival",
		required=True,
		readonly=True,
		states={"draft": [("readonly", False)]},
	)
	checkout = fields.Datetime(
		"Expected-Date-Departure",
		required=True,
		readonly=True,
		states={"draft": [("readonly", False)]},
	)
	adults = fields.Integer(
		readonly=True,
		states={"draft": [("readonly", False)]},
		help="List of adults there in guest list. ",
	)
	infant = fields.Integer('Infant')
	children = fields.Integer(
		readonly=True,
		states={"draft": [("readonly", False)]},
		help="Number of children there in guest list.",
	)
	reservation_line = fields.One2many(
		"hotel.reservation.line",
		"line_id",
		help="Hotel room reservation details.",
		readonly=True,
		states={"draft": [("readonly", False)]},
	)

	service_line_ids = fields.One2many(
		"hotel.service.line",
		"reservation_id",
		help="Hotel room reservation details.",
		readonly=True,
		states={"draft": [("readonly", False)]},
	)

	state = fields.Selection([
			("draft", "Draft"),
			("confirm", "Confirm"),
			("cancel", "Cancel"),
			("done", "Done")],
		readonly=True,
		default="draft")

	folio_id = fields.Many2many(
		"hotel.folio",
		"hotel_folio_reservation_rel",
		"order_id",
		"invoice_id",
		string="Folio",
		copy=False,
	)
	no_of_folio = fields.Integer("No. Folio", compute="_compute_folio_count")
	towel_card = fields.Boolean('Towel Box')
	towel_card_number = fields.Char('Towel Box Number')
	pre_check = fields.Boolean('Is Pre Checked', default=False)
	checkin_id = fields.Many2one('hotel.check', string='Check In')
	checkout_id = fields.Many2one('hotel.check', string='Check Out')
	wait_list = fields.Boolean(string='Waiting List')
	nationality = fields.Many2one('res.partner.nationality', string='Nationality')
	source = fields.Selection(
		[
			("main office", "Main Office"),
			("individual", "Individual"),
			("hotel reservation", "Hotel Reservation"),
			("qouted", "Qouted"),
		],

		default="main office",
	)
	night = fields.Integer("Number of Night")
	note = fields.Text('Remark')
	night_rate_line = fields.One2many('hotel.night.rate.line','reservation_id','Night of Rate')
	manual_rate_line = fields.One2many('hotel.night.rate.line','rate_id','Manual Rate Code')
	type_of_rate = fields.Selection([
			("rate_code", "Rate Code"),
			("night_of_rate", "Night of Rate"),
			("manually", "Manually Rate")], default="rate_code")

	no_of_blocking = fields.Integer("No of Blocking",compute="compute_on_blocking")
	is_show_folio = fields.Boolean('Is Show Folio',compute="compute_on_is_show_folio")
	is_show_split_lines = fields.Boolean('Is Show Split Lines',compute="compute_on_is_show_split_lines")
	is_main_folio_created = fields.Boolean('Is Main Folio created')
	cancel_reason = fields.Selection([('high_rate','High Rate'),('personal_reasons','Personal reasons'),('bad_review','Bad reviews '),('other','Other')],default="high_rate",string="Reason")
	other_reason = fields.Char('Other Reason')
	cancel_date = fields.Date('Cancel Date')
	status = fields.Selection([('confirm','Confirm'),('cancel','Cancel'),('delay_reservation','Delay reservation')],string="Status",default="confirm")
	current_reservation_id = fields.Many2one('hotel.reservation',compute="compute_on_current_id")
	payment_ids = fields.Many2many('account.payment',string='Payments',copy=False)
	all_checkout = fields.Boolean('All Checkout')

	def update_check_out(self):
		for rec in self:
			if rec.split_lines:
				remaining_line = rec.split_lines.filtered(lambda x:not x.checkout_id)
				if remaining_line:
					rec.all_checkout = False
				else:
					rec.all_checkout = True
			else:
				rec.all_checkout = False

	def compute_on_current_id(self):
		for rec in self:
			rec.current_reservation_id = rec.id

	def compute_on_is_show_split_lines(self):
		for rec in self:
			blocking_ids = self.env['split.reservation'].search([('reservation_id','=',rec.id)])
			if blocking_ids and not blocking_ids.filtered(lambda x:x.state == 'draft') and rec.state in ('confirm','done'):
				rec.is_show_split_lines = True
			elif rec.state == 'confirm':
				rec.is_show_split_lines = True
			else:
				rec.is_show_split_lines = False

	def compute_on_is_show_folio(self):
		for rec in self:
			# blocking_ids = self.env['split.reservation'].search([('reservation_id','=',rec.id)])
			# if blocking_ids.split_lines:
			# 	split_lines = blocking_ids.split_lines.filtered(lambda x:not x.check_line)
			# 	if split_lines:
			# 		rec.is_show_folio = True
			# 	else:
			# 		rec.is_show_folio = False
			# elif rec.checkin_id:
			# 	rec.is_show_folio = True
			# else:
			if self.env['hotel.check'].search([('reservation_id','=',rec.id),('state','=','confirm')]):
				rec.is_show_folio = True
			else:
				rec.is_show_folio = False

	def compute_on_blocking(self):
		for rec in self:
			blocking_ids = self.env['split.reservation'].search([('reservation_id','=',rec.id)])
			rec.no_of_blocking = len(blocking_ids)

	@api.onchange('night','checkin')
	def onchange_night_rate_line(self):
		num_lst = self.night_rate_line.mapped('night_number')
		if self.night < len(num_lst):
			for rec in range(len(num_lst),self.night,-1):
				night_rate_line = self.night_rate_line.filtered(lambda x: x.night_number != 'Manual Rate Code')
				night_line = night_rate_line.filtered(lambda x:int(x.night_number.split("Night ")[1]) == rec)
				# self.night_rate_line -= night_line
				self.night_rate_line = [(2,night_line.id)]
		else:
			for rec in range(1,self.night+1):
				old_line = self.night_rate_line.filtered(lambda x:x.night_number == 'Night '+str(rec))
				if not old_line:
					self.night_rate_line = [(0,0,{'night_number':'Night '+str(rec)})]
				remove_line = self.night_rate_line.filtered(lambda x:x.night_number != 'Night '+str(rec))
		if self.manual_rate_line.filtered(lambda x: x.night_number == 'Manual Rate Code'):
			pass
		else:
			self.manual_rate_line = [(0,0,{'night_number':'Manual Rate Code'})]


	@api.onchange('checkin', 'night')
	def onchange_night(self):
		for rec in self:
			if rec.checkin:
				rec.checkout = rec.checkin + timedelta(days=rec.night)

	@api.onchange('checkin')
	@api.constrains('checkin')
	def onchange_date_check(self):
		for rec in self:
			today = fields.Date.today()
			if rec.checkin:
				if rec.checkin.date() < today:
					raise ValidationError(_('Check In Date must be in Future or greater than Current Date'))

	@api.onchange('individual_company')
	def partner_domain(self):
		person_list_items = []
		company_list_items = []
		partners = self.env['res.partner'].search([])
		# person = self.env['res.partner'].search([('company_type', '=', 'person')])
		# company = self.env['res.partner'].search([('company_type', '=', 'company')])
		for partner in partners:
			if partner.company_type == 'person':
				# append all partners from company type person
				person_list_items.append(partner.id)
			else:
				# append all partners from company type company
				company_list_items.append(partner.id)
		if self.individual_company == 'person':
			res = {'domain': {'partner_id': [('id', '=', person_list_items)]}}

		elif self.individual_company == 'company':
			res = {'domain': {'partner_id': [('id', '=', company_list_items)]}}
		return res

	def unlink(self):
		"""
		Overrides orm unlink method.
		@param self: The object pointer
		@return: True/False.
		"""
		lines_of_moves_to_post = self.filtered(
			lambda reserv_rec: reserv_rec.state != "draft"
		)
		if lines_of_moves_to_post:
			raise ValidationError(
				_("Sorry, you can only delete the reservation when it's draft!")
			)
		return super(HotelReservation, self).unlink()

	def copy(self):
		ctx = dict(self._context) or {}
		ctx.update({"duplicate": True})
		return super(HotelReservation, self.with_context(**ctx)).copy()

	@api.model
	def _name_search(self, name, args=None, operator='ilike', limit=100):
		args = args or []
		domain = []
		checkin_rooms = []
		if name:
			checkin_room = self.env['hotel.check.line'].sudo().search(
				[('room_name', 'ilike', name), ('reservation_id.checkin_id', '!=', False),
				 ('reservation_id.all_checkout', '=', False)])
			for no in checkin_room:
				checkin_rooms.append(no.reservation_id.reservation_no)
			if checkin_room:
				domain = [('reservation_no', 'in', checkin_rooms),
						  ]
				print('Domain', domain)
			else:
				domain = [('reservation_no', operator, name), ('checkin_id', '!=', False),
						  ]
		return self._search(domain + args, limit=limit)

	@api.constrains("reservation_line", "adults", "children")
	def _check_reservation_rooms(self):
		"""
		This method is used to validate the reservation_line.
		-----------------------------------------------------
		@param self: object pointer
		@return: raise a warning depending on the validation
		"""
		ctx = dict(self._context) or {}
		for reservation in self:
			# cap = 0
			# for rec in reservation.reservation_line:
			# 	if len(rec.reserve) == 0:
			# 		raise ValidationError(_("Please Select Rooms For Reservation."))
			# 	cap = sum(room.capacity for room in rec.reserve)
			# if not ctx.get("duplicate"):
			# 	if (reservation.adults + reservation.children) > cap:
			# 		raise ValidationError(
			# 			_(
			# 				"Room Capacity Exceeded \n"
			# 				" Please Select Rooms According to"
			# 				" Members Accomodation."
			# 			)
			# 		)
			if reservation.adults <= 0 or reservation.night <= 0:
				raise ValidationError(_("Adults must be more than 0"))

	@api.constrains("checkin", "checkout")
	def check_in_out_dates(self):
		"""
		When date_order is less then check-in date or
		Checkout date should be greater than the check-in date.
		"""
		if self.checkout and self.checkin:
			if self.checkin < self.date_order:
				raise ValidationError(
					_(
						"""Check-in date should be greater than """
						"""the current date."""
					)
				)
			if self.checkout < self.checkin:
				raise ValidationError(
					_("""Check-out date should be greater """ """than Check-in date.""")
				)

	@api.onchange("partner_id")
	def _onchange_partner_id(self):
		"""
		When you change partner_id it will update the partner_invoice_id,
		partner_shipping_id and pricelist_id of the hotel reservation as well
		---------------------------------------------------------------------
		@param self: object pointer
		"""
		if not self.partner_id:
			self.update(
				{
					"partner_invoice_id": False,
					"partner_shipping_id": False,
					"partner_order_id": False,
				}
			)
		else:
			addr = self.partner_id.address_get(["delivery", "invoice", "contact"])
			self.update(
				{
					"partner_invoice_id": addr["invoice"],
					"partner_shipping_id": addr["delivery"],
					# "partner_order_id": addr["contact"],   -------------------> Sahil Thummar 14/7/2023
					"pricelist_id": self.partner_id.property_product_pricelist.id,
				}
			)

	@api.model
	def create(self, vals):
		"""
		Overrides orm create method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		"""
		vals["reservation_no"] = (
				self.env["ir.sequence"].next_by_code("hotel.reservation") or "New"
		)
		return super(HotelReservation, self).create(vals)

	def check_overlap(self, date1, date2):
		delta = date2 - date1
		return {date1 + timedelta(days=i) for i in range(delta.days + 1)}

	def action_register_payment(self):
		journal_id = self.env['account.journal'].search([('type','=','bank')], limit=1)
		return {
			'name': _('Register Payment'),
			'res_model': 'account.payment',
			'view_mode': 'form',
			'context': {
				'default_ref': self.reservation_no,
				'default_partner_id':self.partner_id.id,
				'default_journal_id':journal_id.id if journal_id else False,
				'default_reservation_id':self.id,
				'default_hotel_payment_type':"room_payment",
			},
			'target': 'new',
			'view_id': self.env.ref('hotel_reservation.hotel_account_payment_form').id,
			'type': 'ir.actions.act_window',
		}


	def action_confirmed(self):
		reservation_line_obj = self.env["hotel.room.reservation.line"]
		vals = {}
		for reservation in self:
			rooms = sum(reservation.reservation_line.mapped('no_of_rooms'))
			if rooms >= 1:
				self.state = "confirm"
			else:
				raise ValidationError(
					_(
						"""Please, Select Room Type and No of Room more then 0 """
					)
				)
	
	def confirmed_reservation(self):
		"""
		This method create a new record set for hotel room reservation line
		-------------------------------------------------------------------
		@param self: The object pointer
		@return: new record set for hotel room reservation line.
		"""
		reservation_line_obj = self.env["hotel.room.reservation.line"]
		vals = {}
		for reservation in self:
			reserv_checkin = reservation.checkin
			reserv_checkout = reservation.checkout
			room_bool = False
			for line_id in reservation.reservation_line:
				print ("reservationreservationreservation",reservation)
				for room in line_id.reserve:
					room.is_pre_reserved = True
					if room.room_reservation_line_ids:
						print ("reservationreservatioeeeenreservation",reservation)
						for reserv in room.room_reservation_line_ids.search(
								[
									("status", "in", ("confirm", "done")),
									("room_id", "=", room.id),
								]
						):
							check_in = reserv.check_in
							check_out = reserv.check_out
							# if check_in <= reserv_checkin <= check_out:
							#     room_bool = True
							# if check_in <= reserv_checkout <= check_out:
							#     room_bool = True
							# if (
							#         reserv_checkin <= check_in
							#         and reserv_checkout >= check_out
							# ):
							#     room_bool = True
							r_checkin = (reservation.checkin).date()
							r_checkout = (reservation.checkout).date()
							check_intm = (reserv.check_in).date()
							check_outtm = (reserv.check_out).date()
							range1 = [r_checkin, r_checkout]
							range2 = [check_intm, check_outtm]
							overlap_dates = self.check_overlap(
								*range1
							) & self.check_overlap(*range2)
							print ("room_bool",room_bool)
							if room_bool:
								pass
								# raise ValidationError(
								#     _(
								#         "You tried to Confirm "
								#         "Reservation with room"
								#         " those already "
								#         "reserved in this "
								#         "Reservation Period. "
								#         "Overlap Dates are "
								#         "%s"
								#     )
								#     % overlap_dates
								# )
							else:
								self.state = "confirm"
								vals = {
									"room_id": room.id,
									"check_in": reservation.checkin,
									"check_out": reservation.checkout,
									"state": "assigned",
									"reservation_id": reservation.id,
								}
								# room.write({"isroom": False, "status": "occupied"})
						else:
							print ("444555",reservation)
							self.state = "confirm"
							vals = {
								"room_id": room.id,
								"check_in": reservation.checkin,
								"check_out": reservation.checkout,
								"state": "assigned",
								"reservation_id": reservation.id,
							}
							# room.write({"isroom": False, "status": "occupied"})
					else:
						self.state = "confirm"
						vals = {
							"room_id": room.id,
							"check_in": reservation.checkin,
							"check_out": reservation.checkout,
							"state": "assigned",
							"reservation_id": reservation.id,
						}
						# room.write({"isroom": False, "status": "occupied"})
					reservation_line_obj.create(vals)
		return True
	
	def cancel_reservation(self):
		# """
		# This method cancel record set for hotel room reservation line
		# ------------------------------------------------------------------
		# @param self: The object pointer
		# @return: cancel record set for hotel room reservation line.
		# """
		room_res_line_obj = self.env["hotel.room.reservation.line"]
		hotel_res_line_obj = self.env["hotel.reservation.line"]
		self.state = "cancel"
		room_reservation_line = room_res_line_obj.search(
			[("reservation_id", "in", self.ids)]
		)
		room_reservation_line.write({"state": "unassigned"})
		room_reservation_line.unlink()
		reservation_lines = hotel_res_line_obj.search([("line_id", "in", self.ids)])
		for reservation_line in reservation_lines:
			reservation_line.reserve.write({"isroom": True, "status": "available"})
		return True
	
	def set_to_draft_reservation(self):
		self.update({"state": "draft"})

	def action_send_reservation_mail(self):
		"""
		This function opens a window to compose an email,
		template message loaded by default.
		@param self: object pointer
		"""
		self.ensure_one(), "This is for a single id at a time."
		template_id = self.env.ref(
			"hotel_reservation.email_template_hotel_reservation"
		).id
		compose_form_id = self.env.ref("mail.email_compose_message_wizard_form").id
		ctx = {
			"default_model": "hotel.reservation",
			"default_res_id": self.id,
			"default_use_template": bool(template_id),
			"default_template_id": template_id,
			"default_composition_mode": "comment",
			"force_send": True,
			"mark_so_as_sent": True,
		}
		return {
			"type": "ir.actions.act_window",
			"view_mode": "form",
			"res_model": "mail.compose.message",
			"views": [(compose_form_id, "form")],
			"view_id": compose_form_id,
			"target": "new",
			"context": ctx,
			"force_send": True,
		}

	@api.model
	def reservation_reminder_24hrs(self):
		"""
		This method is for scheduler
		every 1day scheduler will call this method to
		find all tomorrow's reservations.
		----------------------------------------------
		@param self: The object pointer
		@return: send a mail
		"""
		now_date = fields.Date.today()
		template_id = self.env.ref(
			"hotel_reservation.mail_template_reservation_reminder_24hrs"
		)
		for reserv_rec in self:
			checkin_date = reserv_rec.checkin
			difference = relativedelta(now_date, checkin_date)
			if (
					difference.days == -1
					and reserv_rec.partner_id.email
					and reserv_rec.state == "confirm"
			):
				template_id.send_mail(reserv_rec.id, force_send=True)
		return True

	def create_paymaster(self):
		"""
		This method is for create new hotel folio.
		-----------------------------------------
		@param self: The object pointer
		@return: new record set for hotel folio.
		"""
		hotel_folio_obj = self.env["hotel.folio"]
		for reservation in self:
			checkin_date = reservation["checkin"]
			checkout_date = reservation["checkout"]
			duration_vals = self._onchange_check_dates(
				checkin_date=checkin_date,
				checkout_date=checkout_date,
				duration=False,
			)
			duration = duration_vals.get("duration") or 0.0
			folio_lines = []
			folio_vals = {
				"name":reservation.partner_id.name,
				"date_order": reservation.date_order,
				"company_id": reservation.company_id.id,
				"partner_id": reservation.partner_id.id,
				"pricelist_id": reservation.pricelist_id.id,
				"partner_invoice_id": reservation.partner_invoice_id.id,
				"partner_shipping_id": reservation.partner_shipping_id.id,
				"checkin_date": reservation.checkin,
				"checkout_date": reservation.checkin + relativedelta(days=duration),
				"duration": duration,
				"reservation_id": reservation.id,
			}
			# for line in reservation.reservation_line:
			# 	for r in line.reserve:
			# 		folio_lines.append(
			# 			(
			# 				0,
			# 				0,
			# 				{
			# 					"checkin_date": checkin_date,
			# 					"checkout_date": self.checkin + datetime.timedelta(days=reservation.night),
			# 					"product_id": r.product_id and r.product_id.id,
			# 					"name": reservation["reservation_no"],
			# 					"price_unit": r.list_price,
			# 					"product_uom_qty": 1,
			# 					"is_reserved": True,
			# 				},
			# 			)
			# 		)
			# 		r.write({"status": "occupied", "isroom": False})
			# folio_vals.update({"room_line_ids": folio_lines})
			folio = hotel_folio_obj.create(folio_vals)
			self.write({"folio_id": [(4,folio.id)],"is_main_folio_created":True})
			for service in reservation.service_line_ids:
				service.folio_id = folio.id
				service.order_id = folio.order_id.id
			# for rm_line in folio.room_line_ids:
				# rm_line._onchange_product_id()
			# self.write({"folio_id": [(6, 0, folio.ids)],"state":"done"})
		return True

	def create_folio(self):
		"""
		This method is for create new hotel folio.
		-----------------------------------------
		@param self: The object pointer
		@return: new record set for hotel folio.
		"""
		hotel_folio_obj = self.env["hotel.folio"]
		for reservation in self:
			if not reservation.checkin or not reservation.reservation_line and reservation.reservation_line:
				raise ValidationError(
					_(
						"""Before create Folio\n You have to """
						"""Make a Check in Before. """
						"""Add At Least One Room in Reservation Line """
					)
				)
			# split_lines = reservation.split_lines.filtered(lambda x:x.folio_id == False)
			# if not split_lines:
			# 	raise ValidationError(_("All Reservation's Folio Already Created !!!"))
			checkin_date = reservation["checkin"]
			checkout_date = reservation["checkout"]
			duration_vals = self._onchange_check_dates(
				checkin_date=checkin_date,
				checkout_date=checkout_date,
				duration=False,
			)
			duration = duration_vals.get("duration") or 0.0
			blocking_ids = self.env['split.reservation'].search([('reservation_id','=',self.id)],limit=1)
			if blocking_ids:
				if blocking_ids.split_lines.filtered(lambda x:x.check_line and not x.folio_id):
					for split_line in blocking_ids.split_lines.filtered(lambda x:x.check_line and not x.folio_id and x.is_folio):
						price = 0.0
						if split_line.type_of_rate == 'rate_code':
							price = split_line.room_id.list_price
						elif split_line.type_of_rate == 'manually':
							price = split_line.manual_rate_line.rate_code
						
						folio_lines = []
						folio_vals = {
							"name":reservation.partner_id.name + "/" + split_line.partner_id.name,
							"date_order": reservation.date_order,
							"company_id": reservation.company_id.id,
							"partner_id": split_line.partner_id.id,
							"pricelist_id": reservation.pricelist_id.id,
							"partner_invoice_id": split_line.partner_id.id,
							"partner_shipping_id": split_line.partner_id.id,
							"checkin_date": split_line.checkin,
							"checkout_date": split_line.checkin + relativedelta(days=split_line.night),
							"duration": split_line.night,
							"reservation_id": reservation.id,
							'blocking_line':split_line.id,
						}
						if split_line.type_of_rate in ['rate_code','manually']:
							folio_lines.append(
								(0, 0,
									{
										"checkin_date": split_line.checkin,
										"checkout_date": split_line.checkin + datetime.timedelta(days=1),
										"product_id": split_line.check_line.room_name.product_id.id,
										"name": reservation["reservation_no"] + '- Night ',# + str(reservation.night),
										"price_unit": price,
										"product_uom": split_line.check_line.room_name.product_id.uom_id.id,
										"product_uom_qty": 1,
										"is_reserved": True,
									},
								)
							)
						elif split_line.type_of_rate == 'night_of_rate':
							night_count = 1
							checkin_date = split_line.checkin
							for night in split_line.night_rate_line[1]:
								folio_lines.append(
									(0, 0,
										{
											"checkin_date": checkin_date,
											"checkout_date": split_line.checkin + datetime.timedelta(days=1),
											"product_id": split_line.room_id.product_id and split_line.room_id.product_id.id,
											"name": reservation["reservation_no"] +'- Night',#: '+ str(night_count) ,
											"price_unit": split_line.night_rate_line[0].rate_code,
											"product_uom": split_line.room_id.product_id.uom_id.id,
											"product_uom_qty": 1,
											"is_reserved": True,
										},
									))
								checkin_date = split_line.checkin + datetime.timedelta(days=night_count)
								night_count += 1
						
						folio_vals.update({"room_line_ids": folio_lines})
						folio = hotel_folio_obj.create(folio_vals)
						split_line.room_id.write({"status": "occupied", "isroom": False})
						split_line.write({'folio_id':folio.id})
						for service in reservation.service_line_ids:
							service.folio_id = folio.id
							service.order_id = folio.order_id.id
						# for rm_line in folio.room_line_ids:
						# 	rm_line._onchange_product_id()
						self.write({"folio_id": [(4,folio.id)]})
						blocking_line = blocking_ids.split_lines.filtered(lambda x:not x.folio_id)
						if not blocking_line:
							self.write({"state":"done"})
				else:
					raise ValidationError(
								_(
									"""Opps!!!, Not found any guest is check in this reservation..."""
								)
							)
			# else:
			# 	folio_lines = []
			# 	folio_vals = {
			# 		"name":reservation.partner_id.name,
			# 		"date_order": reservation.date_order,
			# 		"company_id": reservation.company_id.id,
			# 		"partner_id": reservation.partner_id.id,
			# 		"pricelist_id": reservation.pricelist_id.id,
			# 		"partner_invoice_id": reservation.partner_invoice_id.id,
			# 		"partner_shipping_id": reservation.partner_shipping_id.id,
			# 		"checkin_date": reservation.checkin,
			# 		"checkout_date": reservation.checkin + relativedelta(days=duration),
			# 		"duration": duration,
			# 		"reservation_id": reservation.id,
			# 	}
			# 	for line in reservation.reservation_line:
			# 		for r in line.reserve:
			# 			folio_lines.append(
			# 				(
			# 					0,
			# 					0,
			# 					{
			# 						"checkin_date": checkin_date,
			# 						"checkout_date": self.checkin + datetime.timedelta(days=reservation.night),
			# 						"product_id": r.product_id and r.product_id.id,
			# 						"name": reservation["reservation_no"],
			# 						"price_unit": r.list_price,
			# 						"product_uom_qty": 1,
			# 						"is_reserved": True,
			# 					},
			# 				)
			# 			)
			# 			r.write({"status": "occupied", "isroom": False})
			# 	folio_vals.update({"room_line_ids": folio_lines})
			# 	folio = hotel_folio_obj.create(folio_vals)
			# 	for service in reservation.service_line_ids:
			# 		service.folio_id = folio.id
			# 		service.order_id = folio.order_id.id
			# 	for rm_line in folio.room_line_ids:
			# 		rm_line._onchange_product_id()
			# 	self.write({"folio_id": [(6, 0, folio.ids)],"state":"done"})
		return True

	def _onchange_check_dates(
			self, checkin_date=False, checkout_date=False, duration=False
	):
		"""
		This method gives the duration between check in checkout if
		customer will leave only for some hour it would be considers
		as a whole day. If customer will checkin checkout for more or equal
		hours, which configured in company as additional hours than it would
		be consider as full days
		--------------------------------------------------------------------
		@param self: object pointer
		@return: Duration and checkout_date
		"""
		value = {}
		configured_addition_hours = self.company_id.additional_hours
		duration = 0
		if checkin_date and checkout_date:
			dur = checkout_date - checkin_date
			duration = dur.days + 1
			if configured_addition_hours > 0:
				additional_hours = abs(dur.seconds / 60)
				if additional_hours <= abs(configured_addition_hours * 60):
					duration -= 1
		value.update({"duration": duration})
		return value

	def open_folio_view(self):
		folios = self.mapped("folio_id")
		action = self.env.ref("hotel.open_hotel_folio1_form_tree_all").read()[0]
		if len(folios) > 1:
			action["domain"] = [("id", "in", folios.ids)]
		elif len(folios) == 1:
			action["views"] = [(self.env.ref("hotel.view_hotel_folio_form").id, "form")]
			action["res_id"] = folios.id
		else:
			action = {"type": "ir.actions.act_window_close"}
		return action

	def open_blocking_view(self):
		blocking_ids = self.env['split.reservation'].search([('reservation_id','=',self.id)])
		xml_id = 'hotel_reservation.split_reservation_tree'
		tree_view_id = self.env.ref(xml_id).id
		xml_id = 'hotel_reservation.split_reservation_form'
		form_view_id = self.env.ref(xml_id).id
		return {
			'name': _('Blocking'),
			'view_mode': 'tree,form',
			'views': [(tree_view_id, 'tree'),(form_view_id, 'form')],
			'res_model': 'split.reservation',
			'domain': [('id','in',blocking_ids.ids)],
			'type': 'ir.actions.act_window',
			}

	def name_get(self, context=None):
		if context is None:
			context = {}
		res = []
		print('context', self.env.context.get('special_display_name'))
		if self.env.context.get('special_display_name'):
			for record in self:
				for rec_line in record.reservation_line:
					for room_line in rec_line.reserve:
						if room_line.name and record.checkin_id:
							res.append((record.id, room_line.name))
			print('line_res', res)
		else:
			for record in self:
				res.append((record.id, record.reservation_no))

		return res



class HotelRoomType(models.Model):
	_inherit = "hotel.room.type"

	def name_get(self):
		res = []
		fname = ""
		print ("........",self._context)
		if self._context.get('reservation'):
			for rec in self:
				no = rec.get_room_no()
				print ("rec ---  NAME GATE",rec)
				fname = str(rec.name) + ' [' + str(no) + ']'
				res.append((rec.id, fname))
		else:
			for rec in self:
				fname = str(rec.name)
				res.append((rec.id, fname))
		return res

	@api.model
	def name_search(self, name="", args=None, operator="ilike", limit=100):
		if args is None:
			args = []
		args += [("name", operator, name)]
		folio = self.search(args, limit=100)
		return folio.name_get()

	def get_room_no(self):
		checkin = datetime.datetime.strptime(self._context.get('checkin'), '%Y-%m-%d %H:%M:%S')
		checkout = datetime.datetime.strptime(self._context.get('checkout'), '%Y-%m-%d %H:%M:%S')
		hotel_room_ids = self.env["hotel.room"].search(
			['|',("room_categ_id", "=", self.id),('room_categ_id','in',self.child_ids.ids)]
		)
		hotel_room_ids = hotel_room_ids.filtered(lambda x:x.is_pre_reserved == False and x.isroom == True)
		room_ids = []
		for room in hotel_room_ids:
			assigned = False
			for line in room.room_reservation_line_ids.filtered(
					lambda l: l.status != "cancel"
			):
				if checkin and line.check_in and checkout:
					if (
							checkin <= line.check_in <= checkout
					) or (
							checkin <= line.check_out <= checkout
					):
						assigned = True
					elif (line.check_in <= checkin <= line.check_out) or (
							line.check_in <= checkout <= line.check_out
					):
						assigned = True
			for rm_line in room.room_line_ids.filtered(lambda l: l.status != "cancel"):
				if checkin and rm_line.check_in and checkout:
					if (
							checkin
							<= rm_line.check_in
							<= checkout
					) or (
							checkin
							<= rm_line.check_out
							<= checkout
					):
						assigned = True
					elif (
							rm_line.check_in <= checkin <= rm_line.check_out
					) or (
							rm_line.check_in <= checkout <= rm_line.check_out
					):
						assigned = True
			if not assigned:
				room_ids.append(room.id)
		return len(room_ids)

class HotelReservationLine(models.Model):
	_name = "hotel.reservation.line"
	_description = "Reservation Line"
	_rec_name = "categ_id"

	name = fields.Char()
	line_id = fields.Many2one("hotel.reservation")
	reserve = fields.Many2many(
		"hotel.room",
		"hotel_reservation_line_room_rel",
		"hotel_reservation_line_id",
		"room_id",
	)
	categ_id = fields.Many2one("hotel.room.type", "Room Type")

	@api.onchange("categ_id")
	def on_change_categ(self):
		"""
		When you change categ_id it check checkin and checkout are
		filled or not if not then raise warning
		-----------------------------------------------------------
		@param self: object pointer
		"""
		if not self.line_id.checkin:
			raise ValidationError(
				_(
					"""Before choosing a room,\n You have to """
					"""select a Check in date or a Check out """
					""" date in the reservation form."""
				)
			)
		hotel_room_ids = self.env["hotel.room"].search(
			['|',("room_categ_id", "=", self.categ_id.id),('room_categ_id','in',self.categ_id.child_ids.ids)]
		)
		hotel_room_ids = hotel_room_ids.filtered(lambda x:x.is_pre_reserved == False and x.isroom == True)
		room_ids = []
		for room in hotel_room_ids:
			assigned = False
			for line in room.room_reservation_line_ids.filtered(
					lambda l: l.status != "cancel"
			):
				if self.line_id.checkin and line.check_in and self.line_id.checkout:
					if (
							self.line_id.checkin <= line.check_in <= self.line_id.checkout
					) or (
							self.line_id.checkin <= line.check_out <= self.line_id.checkout
					):
						assigned = True
					elif (line.check_in <= self.line_id.checkin <= line.check_out) or (
							line.check_in <= self.line_id.checkout <= line.check_out
					):
						assigned = True
			for rm_line in room.room_line_ids.filtered(lambda l: l.status != "cancel"):
				if self.line_id.checkin and rm_line.check_in and self.line_id.checkout:
					if (
							self.line_id.checkin
							<= rm_line.check_in
							<= self.line_id.checkout
					) or (
							self.line_id.checkin
							<= rm_line.check_out
							<= self.line_id.checkout
					):
						assigned = True
					elif (
							rm_line.check_in <= self.line_id.checkin <= rm_line.check_out
					) or (
							rm_line.check_in <= self.line_id.checkout <= rm_line.check_out
					):
						assigned = True
			if not assigned:
				room_ids.append(room.id)
		domain = {"reserve": [("id", "in", room_ids)]}
		return {"domain": domain}

	@api.model
	def create(self, vals):
		"""
		Overrides orm create method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		"""

		res = super(HotelReservationLine, self).create(vals)
		for v in res.reserve:
			v.is_pre_reserved = True

		return res

	def unlink(self):
		"""
		Overrides orm unlink method.
		@param self: The object pointer
		@return: True/False.
		"""
		hotel_room_reserv_line_obj = self.env["hotel.room.reservation.line"]
		for reserv_rec in self:
			for rec in reserv_rec.reserve:
				myobj = hotel_room_reserv_line_obj.search(
					[
						("room_id", "=", rec.id),
						("reservation_id", "=", reserv_rec.line_id.id),
					]
				)
				if myobj:
					rec.write({"isroom": True, "status": "available"})
					myobj.unlink()
		return super(HotelReservationLine, self).unlink()


class HotelRoomReservationLine(models.Model):
	_name = "hotel.room.reservation.line"
	_description = "Hotel Room Reservation"
	_rec_name = "room_id"

	room_id = fields.Many2one("hotel.room")
	check_in = fields.Datetime("Check In Date", required=True)
	check_out = fields.Datetime("Check Out Date", required=True)
	state = fields.Selection(
		[("assigned", "Assigned"), ("unassigned", "Unassigned")], "Room Status"
	)
	reservation_id = fields.Many2one("hotel.reservation", "Reservation")
	status = fields.Selection(string="state", related="reservation_id.state")


class HotelNightRateLine(models.Model):
	_name = 'hotel.night.rate.line'
	_description = 'Hotel Night Rate Line'
	_rec_name = 'night_number'

	reservation_id = fields.Many2one("hotel.reservation", "Reservation")
	rate_id = fields.Many2one("hotel.reservation", "Manually Reservation")
	night_number = fields.Char('Night Number')
	rate_code = fields.Integer('Rate Code')
	blocking_line_id = fields.Many2one('split.reservation.line','Reservation (Blocking)')
	blocking_line_rate_id = fields.Many2one('split.reservation.line','Manually Reservation (Blocking)')
	check_line_id = fields.Many2one('hotel.check','Reservation (Check in/Out)')
	check_line_rate_id = fields.Many2one('hotel.check','Manually Reservation (Check in/Out)')