from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HotelCheckInOut(models.Model):
	_name = 'hotel.check'
	_rec_name = 'reservation_id'
	_order = "reservation_id desc"

	@api.model
	def default_get(self, default_fields):
		result = super(HotelCheckInOut, self).default_get(default_fields)
		return result

	check_type = fields.Selection([
		('check_in', 'Check In'),
		('check_out', 'Check Out'),

	], default='check_in', widget='radio')

	reservation_id = fields.Many2one("hotel.reservation", "Reservation")
	# reservation_room_id = fields.Many2one("hotel.reservation", "Room No.", )
	reservation_room_id = fields.Many2one("hotel.reservation", "Reservation ", )
	check_out_all_rooms = fields.Boolean("Check out all rooms")
	allowed_partner_ids = fields.Many2many('res.partner','rel_res_partner_hotel_check','partner_id','hotel_id',string="Partners")
	partner_id = fields.Many2one("res.partner", "Guest Name")
	# geust_id = fields.Many2one("res.partner", "Guest Name", related='reservation_room_id.partner_id')
	geust_id = fields.Many2one("res.partner", "Guest Name")
	reservation_room = fields.One2many('hotel.check.line', 'check_id', string="Rooms")

	state = fields.Selection(
		[('draft', 'Draft'), ('confirm', 'Confirmed'),
		 ('cancel', 'Cancel')],
		string='State', default='draft', track_visibility='always')
	is_with_blocking = fields.Boolean("Is With Blocking",compute="compute_on_blocking")
	checkin = fields.Datetime('Expected-Date-Arrival',related='reservation_id.checkin')
	checkout = fields.Datetime('Expected-Date-Departure',related='reservation_id.checkout')
	night = fields.Integer("Number of Night")
	is_show_register_payment = fields.Boolean('Is Register Payment',compute="compute_on_register_payment")

	night_rate_line = fields.Many2many('hotel.night.rate.line','blocking_id','night_id','blocking_night_id','Night of Rate')
	manual_rate_line = fields.Many2many('hotel.night.rate.line','blocking_rate_id','manual_id','blocking_manual_id','Manual Rate Code')
	type_of_rate = fields.Selection([
			("rate_code", "Rate Code"),
			("night_of_rate", "Night of Rate"),
			("manually", "Manually Rate")], default="rate_code")
	amount_total = fields.Float("Total Amount",compute="compute_amount_total")
	paid_amount = fields.Float("Paid Amount",compute="compute_amount_total")
	tax_amount = fields.Float("Tax Amount",compute="compute_amount_total")
	amount_residual = fields.Float("Remaining Amount",compute="compute_amount_total")
	allowed_geust_name = fields.Many2many('res.partner','rel_hotel_room_allowed_geust','room_id','check_in_geust',compute="compute_on_allowed_geusts",string='Allowed geusts')
	check_out_room = fields.Many2one('hotel.room',string='Room',domain="[('status','=','occupied')]")
	is_main_guest_use = fields.Boolean("Is Main Guest Use")
	room_person_ids = fields.Many2many("split.reservation.guest.name","rel_check_line_room","check_line_id","person_id",string="Guest Name")
	service_payment_type = fields.Selection([('all_services','All Services'),('my_services','My Services')],default="all_services",string="Sevice Payment Type")
	avl_room_person_ids = fields.Many2many("split.reservation.guest.name","rel_check_a_line_room","check_a_line_id","person_a_id",string="Available Guest Name",compute="compute_on_avl_room_person_ids")

	@api.onchange("is_main_guest_use")
	def onchange_on_main_guest(self):
		for rec in self:
			rec.service_payment_type = "all_services"
			rec.room_person_ids = False

	# @api.onchange("is_main_guest_use","service_payment_type","room_person_ids")
	# def onchange_on_amount(self):
	# 	for rec in self:
	# 		blocking_lines = self.env['split.reservation.line'].search([('room_id','=',rec.check_out_room.id)])
	# 		blocking_lines = blocking_lines.filtered(lambda x:x.reservation_id.state == "done" and not x.checkout_id)
	# 		if blocking_lines:
	# 			total = blocking_lines[0].folio_id.get_totals(rec.is_main_guest_use,rec.room_person_ids.ids,rec.service_payment_type)
	# 			rec.amount_total = total
	# 		else:
	# 			rec.amount_total = 0.0

	@api.depends("check_out_room")
	def compute_on_avl_room_person_ids(self):
		for rec in self:
			blocking_lines = self.env['split.reservation.line'].search([('room_id','=',rec.check_out_room.id)])
			blocking_lines = blocking_lines.filtered(lambda x:x.reservation_id.state == "done" and not x.checkout_id)
			check_out_ids = self.env['hotel.check'].search([('check_type','=','check_out'),('reservation_room_id','=',rec.reservation_room_id.id),('check_out_room','=',rec.check_out_room.id)])
			check_out_guest = check_out_ids.room_person_ids.ids
			if blocking_lines:			
				geust_lines = blocking_lines[0].geust_lines
				if check_out_guest:
					geust_lines = geust_lines.filtered(lambda x:x.id not in check_out_guest)
				rec.avl_room_person_ids = geust_lines
			else:
				rec.avl_room_person_ids = []

	@api.depends('reservation_room_id','check_out_all_rooms','geust_id')
	def compute_on_allowed_geusts(self):
		for rec in self:
			if rec.reservation_room_id:
				rec.allowed_geust_name = [(6,0,rec.reservation_room_id.split_lines.filtered(lambda x:x.is_checkin and not x.checkout_id).mapped('partner_id.id'))]
			else:
				rec.allowed_geust_name = []

	@api.onchange('check_out_room')
	def onchange_on_reservation(self):
		for rec in self:
			# if not self._context.get("no_reflect"):
			blocking_lines = self.env['split.reservation.line'].search([('room_id','=',rec.check_out_room.id)])
			blocking_lines = blocking_lines.filtered(lambda x:x.reservation_id.state == "done" and not x.checkout_id)
			if blocking_lines:
				rec.reservation_room_id = blocking_lines[0].reservation_id.id
				rec.geust_id = blocking_lines[0].partner_id.id

	@api.onchange('reservation_room_id','check_out_all_rooms','geust_id')
	def onchange_on_checkout_room(self):
		for rec in self:
			if not self._context.get("no_reflect"):
				if rec.check_out_all_rooms and rec.reservation_room_id:
					rec.check_out_room = False
				elif rec.geust_id:
					split_line = rec.reservation_room_id.split_lines.filtered(lambda x:x.partner_id == rec.geust_id)
					if split_line:
						rec.check_out_room = split_line.room_id.id
					else:
						rec.check_out_room = False
				else:
					rec.check_out_room = False

	# @api.depends('reservation_room_id','check_out_all_rooms','geust_id')
	# def compute_on_checkout_room(self):
	# 	for rec in self:
	# 		if rec.check_out_all_rooms and rec.reservation_room_id:
	# 			rec.check_out_room = False
	# 		elif rec.geust_id:
	# 			split_line = rec.reservation_room_id.split_lines.filtered(lambda x:x.partner_id == rec.geust_id)
	# 			if split_line:
	# 				rec.check_out_room = split_line.room_id.id
	# 			else:
	# 				rec.check_out_room = False
	# 		else:
	# 			rec.check_out_room = False

	@api.depends('reservation_room_id','check_out_room','geust_id','check_out_all_rooms','is_main_guest_use','service_payment_type','room_person_ids')
	def compute_amount_total(self):
		for rec in self:
			if not rec.check_out_all_rooms:
				blocking_lines = self.env['split.reservation.line'].search([('room_id','=',rec.check_out_room.id)])
				blocking_lines = blocking_lines.filtered(lambda x:x.reservation_id.state == "done" and not x.checkout_id)
				if blocking_lines:
					paid_amount = 0
					if rec.is_main_guest_use and rec.service_payment_type == "my_services":
						paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment" and x.is_main_guest_use and x.partner_id == blocking_lines[0].partner_id).mapped('amount'))				
					elif rec.room_person_ids:
						paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment" and any(x.room_person_ids.filtered(lambda y:y.id in rec.room_person_ids.ids))).mapped('amount'))						
					else:
						paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment" and x.room_person_ids or x.is_main_guest_use).mapped('amount'))						
					total_amount = blocking_lines[0].folio_id.get_totals(rec.is_main_guest_use,rec.room_person_ids.ids,rec.service_payment_type)
					tax_amount = blocking_lines[0].folio_id.service_lines_tax
					rec.amount_total = total_amount
					rec.paid_amount = paid_amount
					rec.tax_amount = tax_amount
					rec.amount_residual = total_amount - paid_amount				
				else:
					rec.amount_total = 0.0
					rec.paid_amount = 0.0
					rec.tax_amount = 0.0
					rec.amount_residual = 0.0
			else:
				paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment").mapped('amount'))				
				total_amount = 0
				tax_amount = 0
				for folio in rec.reservation_room_id.folio_id:
					total_amount += folio.service_lines_total
					total_amount += folio.rooms_lines_total
					total_amount += folio.amount_tax
					tax_amount += folio.service_lines_tax
				rec.amount_total = total_amount
				rec.paid_amount = paid_amount
				rec.tax_amount = tax_amount
				rec.amount_residual = total_amount - paid_amount
				
			# elif rec.check_out_all_rooms and rec.reservation_room_id:
			# 	total_amount = 0
			# 	tax_amount = 0
			# 	paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment").mapped('amount'))
			# 	#paid_amount = sum(rec.reservation_room_id.payment_ids.mapped('amount'))
			# 	for folio in rec.reservation_room_id.folio_id:
			# 		rooms_total = folio.rooms_lines_total
			# 		service_total = folio.service_lines_total
			# 		#total_amount += rooms_total # Remove  20 Sept
			# 		total_amount += service_total
			# 		total_amount += services_total
			# 		total_amount += folio.amount_tax
			# 		tax_amount += folio.service_lines_tax
			# 	rec.amount_total = total_amount
			# 	rec.paid_amount = paid_amount
			# 	rec.tax_amount = tax_amount
			# 	rec.amount_residual = total_amount - paid_amount
			# elif rec.geust_id:
			# 	folio_id = rec.reservation_room_id.folio_id.filtered(lambda x:x.partner_id == rec.geust_id)
			# 	paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment" and x.partner_id == rec.geust_id).mapped('amount'))
			# 	#paid_amount = sum(rec.reservation_room_id.payment_ids.filtered(lambda x:x.partner_id == rec.geust_id).mapped('amount'))
			# 	if folio_id:
			# 		rooms_total = folio_id.rooms_lines_total
			# 		service_total = folio_id.service_lines_total
			# 		amount_total = service_total #rooms_total
			# 		amount_tax = folio_id.service_lines_tax #amount_tax
			# 		rec.amount_total = amount_total + amount_tax
			# 		rec.paid_amount = paid_amount
			# 		rec.tax_amount = amount_tax
			# 		rec.amount_residual = amount_total - paid_amount
			# 	else:
			# 		rec.amount_total = 0.0
			# 		rec.paid_amount = 0.0
			# 		rec.tax_amount = 0.0
			# 		rec.amount_residual = 0.0
			# else:
			# 	rec.amount_total = 0.0
			# 	rec.paid_amount = 0.0
			# 	rec.tax_amount= 0.0
			# 	rec.amount_residual = 0.0

	@api.onchange("reservation_room_id","geust_id","check_out_room")
	def onchange_on_night_from_checkout(self):
		for rec in self:
			if rec.check_type == "check_out" and rec.reservation_room_id and rec.check_out_all_rooms:
				rec.night = rec.reservation_room_id.night
			elif rec.check_type == "check_out" and rec.geust_id:
				split_line = rec.reservation_room_id.split_lines.filtered(lambda x:x.partner_id == rec.geust_id)
				if split_line:
					rec.night = split_line.night
			else:
				rec.night = 0

	@api.onchange('manual_rate_line','night_rate_line')
	def change_rate_values(self):
		for rec in self:
			ReservationObj = self.env['split.reservation'].search([('reservation_id','=',self.reservation_id.id)])
			split_lines = ReservationObj.split_lines.filtered(lambda line:line.partner_id == self.partner_id)
			for split_line in split_lines:
				for number in range(0,len(rec.night_rate_line)):
					split_line.night_rate_line[number].rate_code = rec.night_rate_line[number].rate_code
				if split_line.manual_rate_line and rec.manual_rate_line:
					split_line.manual_rate_line[0].rate_code = rec.manual_rate_line[0].rate_code

	def add_night_rate_lines(self,type_of_rate=False,night_rate_line=False):
		for rec in self:
			if rec.reservation_room:
				if rec.reservation_room[0].blocking_line:
					c_night_rate_line = rec.reservation_room[0].blocking_line.night_rate_line.ids
					manual_rate_line = rec.reservation_room[0].blocking_line.manual_rate_line.ids
					if night_rate_line:
						rec.night_rate_line = [(6,0,night_rate_line.ids)]
					else:
						rec.night_rate_line = [(6,0,c_night_rate_line)]
					rec.manual_rate_line = [(6,0,manual_rate_line)]
					if type_of_rate:
						rec.type_of_rate = type_of_rate
					else:
						rec.type_of_rate = rec.reservation_room[0].blocking_line.type_of_rate

	def compute_on_register_payment(self):
		for rec in self:
			if rec.reservation_room:
				if rec.reservation_room[0].blocking_line.folio_id:
					folio_id = rec.reservation_room[0].blocking_line.folio_id
					if folio_id.hotel_invoice_id and folio_id.hotel_invoice_id.state == 'posted' and folio_id.hotel_invoice_id.amount_residual:
						rec.is_show_register_payment = True
					else:
						rec.is_show_register_payment = False
				else:
					rec.is_show_register_payment = False
			else:
				rec.is_show_register_payment = False

	@api.depends('reservation_id')
	def compute_on_blocking(self):
		for rec in self:
			if rec.reservation_id:
				split_lines = self.env['split.reservation'].search([('reservation_id','=',rec.reservation_id.id)])
				if split_lines:
					rec.is_with_blocking = True
				else:
					rec.is_with_blocking = False
			else:
				rec.is_with_blocking = False

	@api.onchange("reservation_id")
	def on_reservation_change_guest(self):
		for res in self:
			if res.reservation_id:
				ReservationObj = self.env['split.reservation'].search([('reservation_id','=',res.reservation_id.id)])
				reservation_lines = res.reservation_id.reservation_line
				# res.reservation_room.unlink()
				res.reservation_room -= res.reservation_room 
				lines = []
				if ReservationObj:
					res.partner_id = False
					partner_ids = ReservationObj.split_lines.mapped('partner_id.id')
					checked_in = self.env['hotel.check'].search([('partner_id','in',partner_ids),('reservation_id','=',res.reservation_id.id)])
					not_allowed_partners = checked_in.mapped('partner_id.id')
					allowed_partners = self.env['res.partner'].search([('id','in',partner_ids),('id','not in',not_allowed_partners)])
					res.allowed_partner_ids = [(6,0,allowed_partners.ids)]
				elif reservation_lines:
					for reservation_line in reservation_lines:
						lines.append((0, 0,{'room_type':reservation_line.categ_id.id,'reservation_line':reservation_line.id}))
					res.allowed_partner_ids = [(6,0,[res.reservation_id.partner_id.id])]
					res.partner_id = res.reservation_id.partner_id.id
					res.night = res.reservation_id.night
				res.reservation_room = lines
				for reservation_room in res.reservation_room:
					reservation_room.allowed_room_name = [(6,0,reservation_room.get_available_rooms())]
				self.add_night_rate_lines()

	@api.onchange('partner_id')
	def onchange_on_room(self):
		if self.partner_id and self.is_with_blocking:
			self.reservation_room -= self.reservation_room
			ReservationObj = self.env['split.reservation'].search([('reservation_id','=',self.reservation_id.id)])
			split_lines = ReservationObj.split_lines.filtered(lambda line:line.partner_id == self.partner_id)
			lines = []
			for spl in split_lines:
				if spl.room_id:
					self.night = spl.night
					lines.append((0, 0,{'room_type':spl.room_type_id.id,'room_name':spl.room_id.id if spl.room_id else False,'reservation_line':spl.reservation_line.id,'blocking_line':spl.id}))
			self.reservation_room = lines
			for reservation_room in self.reservation_room:
				reservation_room.allowed_room_name = [(6,0,reservation_room.get_available_rooms())]
			self.add_night_rate_lines()

	@api.onchange('night','type_of_rate')
	def onchange_on_night(self):
		for rec in self:
			ReservationObj = self.env['split.reservation'].search([('reservation_id','=',self.reservation_id.id)])
			split_lines = ReservationObj.split_lines.filtered(lambda line:line.partner_id == self.partner_id)
			for split_line in split_lines:
				if rec.night and split_line:
					split_line.night = self.night
					split_line.type_of_rate = self.type_of_rate
					split_line.onchange_night()
					split_line.onchange_night_rate_line()
				elif rec.night and rec.reservation_id:
					rec.reservation_id.night = rec.night
					rec.reservation_id.onchange_night()
				elif rec.reservation_id:
					raise UserError(_("Number Of Night Must be more than 1"))
			rec.add_night_rate_lines()

	@api.model
	def create(self, vals):
		"""
		Overrides orm create method.
		@param self: The object pointer
		@param vals: dictionary of fields value.
		"""
		reseravation = self.env["hotel.reservation"].sudo().search([('id', '=', vals["reservation_id"])])
		reseravation.pre_check = True
		return super(HotelCheckInOut, self).create(vals)

	def confirm(self):
		for record in self:	
			if record.check_type == 'check_in':
				blank_room_line = record.reservation_room.filtered(lambda line:not line.room_name)
				if blank_room_line:
					raise UserError(_("Please Select Rooms !!!"))

				if record.reservation_id.reservation_line:
					for reservation_line in record.reservation_room:
						if reservation_line.reservation_line:
							reservation_line.room_name.is_out_order = True
							reservation_line.room_name.status = "occupied"
							reservation_line.blocking_line.check_line = reservation_line.id
							reservation_line.blocking_line.checkin = fields.datetime.now()
							reservation_line.blocking_line.is_checkin = True
							reservation_line.blocking_line.room_id = reservation_line.room_name.id
							reservation_line.reservation_line.reserve = [(4,reservation_line.room_name.id)]

				# for reservation in record.reservation_id.reservation_line:
				# 	rooms = []
				# 	for reservation_line in reservation.reserve:
				# 		for room in record.reservation_room:
				# 			if reservation_line.room_categ_id.id == room.room_type.id:
				# 				reservation_line = room.room_name
				# 				room.room_name.is_out_order = True
				# 				room.room_name.status = "occupied"
				# 				rooms.append(room.room_name.id)
				# 	reservation.reserve = [(6, 0, rooms)]
				record.reservation_id.checkin_id = record.id
				record.reservation_id.checkin = fields.datetime.now()
				record.write({"state": "confirm"})
			elif record.check_type == 'check_out':
				if record.is_main_guest_use:
					if record.service_payment_type == "my_services":
						check_out_ids = self.env['hotel.check'].search([('reservation_room_id','=',record.reservation_room_id.id),('check_out_room','=',record.check_out_room.id)])
						check_out_persons = check_out_ids.room_person_ids.ids
						blocking_lines = self.env['split.reservation.line'].search([('room_id','=',record.check_out_room.id)])
						blocking_lines = blocking_lines.filtered(lambda x:x.reservation_id.state == "done" and not x.checkout_id)
						if blocking_lines:
							for geust in blocking_lines[0].geust_lines:
								if geust.id not in check_out_persons:
									raise UserError(_("Your Room Guest %s 's Check Out Is Remain !!!") % (geust.name))

					# if record.partner_id.payment_amount_due == 0:
					# 	record.reservation_room_id.checkout_id = record.id
					# 	for reservation in record.reservation_id.reservation_line:

					# 		for reservation_line in reservation.reserve:
					# 			for room in record.reservation_room:
					# 				if reservation_line.room_categ_id.id == room.room_type.id:
					# 					room.room_name.is_out_order = True
					# 					room.room_name.status = "available"

					# 	record.write({"state": "confirm"})
					# else:
					# 	return {
					# 		'name': _("Contact Payments"),
					# 		'type': 'ir.actions.act_window',
					# 		'view_mode': 'kanban,tree,form',
					# 		'res_model': 'res.partner',
					# 		'domain': [('id', '=', self.partner_id.id)]
					# 	}
					if record.check_out_all_rooms and record.reservation_room_id:
						if record.reservation_room_id.split_lines.filtered(lambda x:not x.is_checkin):
							raise UserError(_("Some Rooms are not checked in yet !!!"))
						# paid_amount = sum(record.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment").mapped('amount'))
						paid_amount = sum(record.reservation_room_id.payment_ids.mapped('amount'))
						if paid_amount < self.amount_total:
							raise UserError(_("Please Pay Service's and Room's Payment !!!"))
						folio_id = record.reservation_room_id.folio_id.filtered(lambda x:x.partner_id == self.geust_id)
						if record.geust_id:
							# if folio_id.state != "done":
								# raise UserError(_("First Finish Reseravation's Folio Process !!!"))
							# for reservation in record.reservation_room_id.reservation_line:
							for split_line in record.reservation_room_id.split_lines:
								split_line.checkout_id = record.id
								split_line.room_id.is_out_order = True
								split_line.room_id.status = "available"
							record.write({"state": "confirm"})
							record.reservation_room_id.update_check_out()
					elif record.geust_id and not record.check_out_all_rooms:
						# paid_amount = sum(record.reservation_room_id.payment_ids.filtered(lambda x:x.hotel_payment_type == "service_payment" and x.partner_id == record.geust_id).mapped('amount'))
						paid_amount = sum(record.reservation_room_id.payment_ids.filtered(lambda x:x.partner_id == record.geust_id).mapped('amount'))
						if paid_amount < self.amount_total:
							raise UserError(_("Please Pay Service's and Room's Payment !!!"))
						# folio_id = record.reservation_room_id.folio_id.filtered(lambda x:x.state != "done")
						split_line = record.reservation_room_id.split_lines.filtered(lambda x:x.partner_id == record.geust_id)
						# if folio_id:
							# raise UserError(_("First Finish Reseravation's Folio Process !!!"))
						record.check_out_room.is_out_order = True 
						record.check_out_room.status = "available"
						split_line.checkout_id = record.id
						record.write({"state": "confirm"})
						record.reservation_room_id.update_check_out()
				else:
					if record.paid_amount < record.amount_total:
						raise UserError(_("Please Pay Service's Amount !!!"))					
					record.write({"state": "confirm"})

	def action_cancel(self):
		""" Action Cancel """
		self.write({
			'state': 'cancel'
		})

	def unlink(self):
		for rec in self:
			if rec.state != "draft":
				raise UserError(_("Sorry, you can only delete the when it's draft !"))
		res = super(HotelCheckInOut, self).unlink()
		return res

	def action_register_payment(self):
		# for rec in self:
		# 	if rec.reservation_room:
		# 		if rec.reservation_room[0].blocking_line.folio_id:
		# 			folio_id = rec.reservation_room[0].blocking_line.folio_id
		# 			if folio_id.hotel_invoice_id and folio_id.hotel_invoice_id.state == 'posted':
		# 				return folio_id.hotel_invoice_id.action_register_payment()
		reservation_id = self.env['hotel.reservation']
		if self.check_type == "check_in" and self.reservation_id:
			reservation_id = self.reservation_id
		elif self.check_type == "check_out" and self.reservation_room_id:
			reservation_id = self.reservation_room_id
		if reservation_id:
			journal_id = self.env['account.journal'].search([('type','=','bank')], limit=1)
			return {
				'name': _('Register Payment'),
				'res_model': 'account.payment',
				'view_mode': 'form',
				'context': {
					'default_ref': reservation_id.reservation_no,
					'default_partner_id':self.partner_id.id if self.check_type == "check_in" else self.geust_id.id,
					'default_journal_id':journal_id.id if journal_id else False,
					'default_reservation_id':reservation_id.id,
					'default_hotel_payment_type':"room_payment" if self.check_type == "check_in" else "service_payment",
					'default_amount': self.amount_residual,
					'default_room_person_ids': self.room_person_ids.ids,
					'default_is_main_guest_use': self.is_main_guest_use,
				},
				'target': 'new',
				'view_id': self.env.ref('hotel_reservation.hotel_account_payment_form').id,
				'type': 'ir.actions.act_window',
			}

class HotelCheckInOutLine(models.Model):
	_name = 'hotel.check.line'
	_rec_name = 'room_type'
	
	check_id = fields.Many2one('hotel.check', string='Check ID')
	reservation_id = fields.Many2one(
		"hotel.reservation", "Reservation"
	)
	room_type = fields.Many2one('hotel.room.type', string='Room Type')
	allowed_room_name = fields.Many2many('hotel.room','rel_hotel_check_hotel_room','check_line','room_id','Allowed Rooms')
	room_name = fields.Many2one('hotel.room',string="Room Number")
	room_number = fields.Char(related='room_name.name', string="Room Name")
	reservation_line = fields.Many2one('hotel.reservation.line', string='Reservation Line')
	blocking_line = fields.Many2one('split.reservation.line','blocking line')

	def get_available_rooms(self):
		"""
		When you change room_type it check checkin and checkout are
		filled or not if not then raise warning
		-----------------------------------------------------------
		@param self: object pointer
		"""
		if not self.check_id.checkin:
			raise ValidationError(
				_(
					"""Before choosing a room,\n You have to """
					"""select a Check in date or a Check out """
					""" date in the reservation form."""
				)
			)
		hotel_room_ids = self.env["hotel.room"].search(
			['|',("room_categ_id", "=", self.room_type.id),('room_categ_id','in',self.room_type.child_ids.ids)]
		)
		hotel_room_ids = hotel_room_ids.filtered(lambda x:x.is_pre_reserved == False and x.isroom == True)
		room_ids = []
		for room in hotel_room_ids:
			assigned = False
			for line in room.room_reservation_line_ids.filtered(
					lambda l: l.status != "cancel"
			):
				if self.check_id.checkin and line.check_in and self.check_id.checkout:
					if (
							self.check_id.checkin <= line.check_in <= self.check_id.checkout
					) or (
							self.check_id.checkin <= line.check_out <= self.check_id.checkout
					):
						assigned = True
					elif (line.check_in <= self.check_id.checkin <= line.check_out) or (
							line.check_in <= self.check_id.checkout <= line.check_out
					):
						assigned = True
			for rm_line in room.room_line_ids.filtered(lambda l: l.status != "cancel"):
				if self.check_id.checkin and rm_line.check_in and self.check_id.checkout:
					if (
							self.check_id.checkin
							<= rm_line.check_in
							<= self.check_id.checkout
					) or (
							self.check_id.checkin
							<= rm_line.check_out
							<= self.check_id.checkout
					):
						assigned = True
					elif (
							rm_line.check_in <= self.check_id.checkin <= rm_line.check_out
					) or (
							rm_line.check_in <= self.check_id.checkout <= rm_line.check_out
					):
						assigned = True
			if not assigned:
				room_ids.append(room.id)
		return room_ids
	
	@api.depends("reservation_id")
	def _get_type_domain(self):
		room_types = []
		print ("CAAAAAAAAAAAAAAA")
		for rec in self.reservation_id.reservation_line:
			for room_type in rec.reserve:
				if room_type.room_categ_id:
					room_types.append(room_type.room_categ_id.id)
		self.room_type_list = [(6, 0, room_types)]

	room_type_list = fields.Many2many('hotel.room.type', store=True, compute=_get_type_domain)
