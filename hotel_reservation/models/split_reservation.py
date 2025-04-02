# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta, date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError , UserError
import datetime

class SplitReservationGuestName(models.Model):
	_name = "split.reservation.guest.name"
	_description = "Split Reservation Guest Name"

	name = fields.Char('Name')
	split_line_id = fields.Many2one('split.reservation.line')

class SplitReservationLine(models.Model):
	_name = "split.reservation.line"
	_description = "Reservation Line"

	def _default_domain(self):
		hotel_room_ids = self.env["hotel.room"].search([('room_categ_id','=',self.room_type_id.id)])
		hotel_room_ids = hotel_room_ids.filtered(lambda x: x.isroom == True)
		room_ids = []
		for room in hotel_room_ids:
			assigned = False
			for line in room.room_reservation_line_ids.filtered(
					lambda l: l.status != "cancel"
			):
				if self.spli_reservation_id.checkin and line.check_in and self.spli_reservation_id.checkout:
					if (
							self.spli_reservation_id.checkin <= line.check_in <= self.spli_reservation_id.checkout
					) or (
							self.spli_reservation_id.checkin <= line.check_out <= self.spli_reservation_id.checkout
					):
						assigned = True
					elif (line.check_in <= self.spli_reservation_id.checkin <= line.check_out) or (
							line.check_in <= self.spli_reservation_id.checkout <= line.check_out
					):
						assigned = True
			for rm_line in room.room_reservation_line_ids.filtered(lambda l: l.status != "cancel"):
				if self.spli_reservation_id.checkin and rm_line.check_in and self.spli_reservation_id.checkout:
					if (
							self.spli_reservation_id.checkin
							<= rm_line.check_in
							<= self.spli_reservation_id.checkout
					) or (
							self.spli_reservation_id.checkin
							<= rm_line.check_out
							<= self.spli_reservation_id.checkout
					):
						assigned = True
					elif (
							rm_line.check_in <= self.spli_reservation_id.checkin <= rm_line.check_out
					) or (
							rm_line.check_in <= self.spli_reservation_id.checkout <= rm_line.check_out
					):
						assigned = True
			if not assigned:
				room_ids.append(room.id)
		print ("room_ids",room_ids)
		return [("id", "in", room_ids)]

	spli_reservation_id = fields.Many2one('split.reservation', string='Split Reservation')
	partner_id = fields.Many2one('res.partner', string='Guest Name')
	no_of_person = fields.Integer('No of Person')
	room_type_id = fields.Many2one('hotel.room.type', string='Rooms Type')
	room_id = fields.Many2one('hotel.room', string='Room Number', domain=_default_domain)
	reservation_id = fields.Many2one('hotel.reservation', string='Reservation')
	reservation_line = fields.Many2one('hotel.reservation.line', string='Reservation Line')
	check_line = fields.Many2one('hotel.check.line','Check Line')
	folio_id = fields.Many2one("hotel.folio",string="Folio")
	checkin = fields.Datetime('Expected-Date-Arrival')
	checkout = fields.Datetime("Expected-Date-Departure")
	is_checkin = fields.Boolean('Check In')
	is_folio = fields.Boolean('Folio')
	night = fields.Integer("Number of Night")

	night_rate_line = fields.One2many('hotel.night.rate.line','blocking_line_id','Night of Rate')
	manual_rate_line = fields.One2many('hotel.night.rate.line','blocking_line_rate_id','Manual Rate Code')
	type_of_rate = fields.Selection([
			("rate_code", "Rate Code"),
			("night_of_rate", "Night of Rate"),
			("manually", "Manually Rate")], default="rate_code")
	geust_lines = fields.One2many('split.reservation.guest.name','split_line_id','Guest Names')
	checkout_id = fields.Many2one('hotel.check', string='Check Out')

	@api.onchange('type_of_rate')
	def add_night_rate_lines_in_check(self):
		for rec in self:
			check_line = self.env['hotel.check.line'].search([('blocking_line','=',rec.id)])
			check_line.check_id.add_night_rate_lines(type_of_rate=rec.type_of_rate,night_rate_line=rec.night_rate_line)

	@api.onchange("room_id")
	def onchange_room(self):
		if not self.partner_id:
			raise ValidationError(_('Please first select guest then after select room.'))
		exist_room = self.spli_reservation_id.split_lines.filtered(lambda x:x.room_id == self.room_id and x.id != self.id)
		if exist_room:
			raise ValidationError(_('You Cannot Select Same Room, Please Select Another Room .'))

	@api.onchange("partner_id")
	def on_change_guest(self):
		"""
		When you change categ_id it check checkin and checkout are
		filled or not if not then raise warning
		-----------------------------------------------------------
		@param self: object pointer
		"""
		print ("\n\n\n === >  >> > > >on_change_gueston_change_gueston_change_guest",self)
		hotel_room_ids = self.env["hotel.room"].search([('room_categ_id','=',self.room_type_id.id)])
		print ("hotel_room_ids",hotel_room_ids)
		hotel_room_ids = hotel_room_ids.filtered(lambda x: x.isroom == True)
		print ("hotel_room_ids",hotel_room_ids)
		room_ids = []
		for room in hotel_room_ids:
			assigned = False
			for line in room.room_reservation_line_ids.filtered(
					lambda l: l.status != "cancel"
			):
				if self.spli_reservation_id.checkin and line.check_in and self.spli_reservation_id.checkout:
					if (
							self.spli_reservation_id.checkin <= line.check_in <= self.spli_reservation_id.checkout
					) or (
							self.spli_reservation_id.checkin <= line.check_out <= self.spli_reservation_id.checkout
					):
						assigned = True
					elif (line.check_in <= self.spli_reservation_id.checkin <= line.check_out) or (
							line.check_in <= self.spli_reservation_id.checkout <= line.check_out
					):
						assigned = True
			for rm_line in room.room_reservation_line_ids.filtered(lambda l: l.status != "cancel"):
				if self.spli_reservation_id.checkin and rm_line.check_in and self.spli_reservation_id.checkout:
					if (
							self.spli_reservation_id.checkin
							<= rm_line.check_in
							<= self.spli_reservation_id.checkout
					) or (
							self.spli_reservation_id.checkin
							<= rm_line.check_out
							<= self.spli_reservation_id.checkout
					):
						assigned = True
					elif (
							rm_line.check_in <= self.spli_reservation_id.checkin <= rm_line.check_out
					) or (
							rm_line.check_in <= self.spli_reservation_id.checkout <= rm_line.check_out
					):
						assigned = True
			if not assigned:
				room_ids.append(room.id)
		domain = {"room_id": [("id", "in", room_ids)]}
		return {"domain": domain}

	@api.onchange('night','checkin')
	def onchange_night_rate_line(self):
		num_lst = self.night_rate_line.mapped('night_number')
		if self.night < len(num_lst):
			for rec in range(len(num_lst),self.night,-1):
				night_rate_line = self.night_rate_line.filtered(lambda x: x.night_number != 'Manual Rate Code')
				night_line = night_rate_line.filtered(lambda x:int(x.night_number.split("Night ")[1]) == rec)
				self.night_rate_line -= night_line
				# self.night_rate_line = [(2,night_line.id)]
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
		self.add_night_rate_lines_in_check()

	@api.onchange('checkin', 'night')
	def onchange_night(self):
		for rec in self:
			if rec.checkin:
				rec.checkout = rec.checkin + timedelta(days=rec.night)
				self.add_night_rate_lines_in_check()

	@api.onchange('checkin')
	@api.constrains('checkin')
	def onchange_date_check(self):
		for rec in self:
			today = fields.Date.today()
			if rec.checkin:
				if rec.checkin.date() < today:
					raise ValidationError(_('Check In Date must be in Future or greater than Current Date'))

class HotelReservation(models.Model):
	_inherit = "hotel.reservation"

	split_lines = fields.One2many('split.reservation.line','reservation_id', string='Split Lines')
	is_show_split = fields.Boolean("Is Show Split Button",compute="compute_on_show_split")

	@api.depends('reservation_line.no_of_rooms','state')
	def compute_on_show_split(self):
		for rec in self:
			split_lines = self.env['split.reservation'].search([('reservation_id','=',rec.id)])
			print ("split_lines",split_lines)
			if rec.state =='confirm' and not split_lines:
				multi_line = sum(rec.reservation_line.mapped('no_of_rooms'))
				if multi_line > 1:
					rec.is_show_split = True
				else:
					rec.is_show_split = False
			else:
				rec.is_show_split = False

	def action_reservation_split(self):
		if not self.reservation_line:
			raise UserError(_("Please Select Rooms"))
		else:
			split_lines = []
			night_rate_line = []
			manual_rate_line = []
			for night_rate in self.night_rate_line:
				night_rate_line.append((0,0,{
					'night_number':night_rate.night_number,
					'rate_code':night_rate.rate_code,
				}))
			for manual_rate in self.manual_rate_line:
				manual_rate_line.append((0,0,{
					'night_number':manual_rate.night_number,
					'rate_code':manual_rate.rate_code,
				}))
			for reservation_line in self.reservation_line:
				for room in range(1,reservation_line.no_of_rooms+1):
					split_lines.append([0,0,{
						'night':self.night,
						'room_type_id':reservation_line.categ_id.id,
						'reservation_line':reservation_line.id,
						'reservation_id':self.id,
						'type_of_rate':self.type_of_rate,
						'night_rate_line':night_rate_line,
						'manual_rate_line':manual_rate_line,
						'checkin':self.checkin,
						'checkout':self.checkout,
					}])
			if split_lines:
				blocking_id = self.env['split.reservation'].create({'reservation_id':self.id,'split_lines':split_lines})
			else:
				raise UserError(_("Please, Room Type of agent no of rooms!!!"))

class HotelReservationLine(models.Model):
	_inherit = "hotel.reservation.line"

	no_of_rooms = fields.Integer("No of Rooms")

class SplitReservation(models.Model):
	_name = "split.reservation"
	_description = "Reservation"
	_rec_name = "reservation_id"
	_inherit = ["mail.thread"]

	reservation_id = fields.Many2one('hotel.reservation', string='Reservation')
	state  = fields.Selection([('draft','Draft'),('lock','Lock')], default='draft')
	split_lines = fields.One2many('split.reservation.line','spli_reservation_id', string='Split Lines')
	checkin = fields.Datetime('Expected-Date-Arrival',related='reservation_id.checkin')
	checkout = fields.Datetime('Expected-Date-Departure',related='reservation_id.checkout')
	partner_id = fields.Many2one(string='Guest Name', related='reservation_id.partner_id')
	reservation_state = fields.Selection(string='Reservation Status', related='reservation_id.state')
	no_of_folio = fields.Integer(related="reservation_id.no_of_folio")

	def action_lock(self):
		split_lines = self.split_lines.filtered(lambda x:x.no_of_person > 0 and (x.no_of_person-1) > len(x.geust_lines))
		if split_lines:
			raise UserError(_("Plase fill up all guest's name !!!"))
		blank = self.split_lines.filtered(lambda x: not x.room_id)
		if blank:
			raise UserError(_("Please, Select Room for all lines !!!"))
		else:
			self.state = 'lock'
			# for line in self.reservation_id.reservation_line:
			# 	split_lines = self.split_lines.filtered(lambda x:x.reservation_line.id == line.id)
			# 	line.reserve = [(6,0,split_lines.mapped('room_id.id'))]
			self.reservation_id.confirmed_reservation()
			self.split_lines.room_id.status = "occupied"

	def open_folio_view(self):
		folios = self.reservation_id.mapped("folio_id")
		action = self.env.ref("hotel.open_hotel_folio1_form_tree_all").read()[0]
		if len(folios) > 1:
			action["domain"] = [("id", "in", folios.ids)]
		elif len(folios) == 1:
			action["views"] = [(self.env.ref("hotel.view_hotel_folio_form").id, "form")]
			action["res_id"] = folios.id
		else:
			action = {"type": "ir.actions.act_window_close"}
		return action





