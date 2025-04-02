# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from datetime import timedelta , datetime , date


class TransferRequestWizard(models.Model):
	_name = "transfer.request.wizard"
	_description = "Transfer Request Wizard"

	def get_old_room(self):
		room_obj = self.env["hotel.room"]
		active_id = self._context.get('active_id')
		folio_id = self.env['hotel.folio'].browse(int(active_id))
		product_id = folio_id.room_close_id.product_id if folio_id.room_close_id else False
		if not product_id:
			last_room_line = folio_id.room_line_ids[-1]
			product_id = last_room_line.product_id
		prod_room = room_obj.search([("product_id", "=", product_id.id)], limit=1)		
		return prod_room

	def get_reservation(self):
		active_id = self._context.get('active_id')
		folio_id = self.env['hotel.folio'].browse(int(active_id))		
		return folio_id.reservation_id

	name = fields.Char("Name")
	date_transfer = fields.Date('Transfer Date',default=date.today())
	old_room_id = fields.Many2one('hotel.room','Old Room',default=get_old_room)
	available_room_ids = fields.Many2many('hotel.room','rel_transfer_request_hotel_room','transfer_request_id','hotel_room_id','Hotel Rooms',compute="compute_on_aval_room")
	new_room_id = fields.Many2one('hotel.room','New Room')
	transfer_type = fields.Selection([('same_type','Same Type'),('other_type','Other Type')],default="same_type",string="Transfer To")
	reservation_id = fields.Many2one('hotel.reservation','Reservation',default=get_reservation)
	reason = fields.Char('Reason')

	@api.depends('transfer_type')
	def compute_on_aval_room(self):
		for rec in self:
			active_id = self._context.get('active_id')
			folio_id = self.env['hotel.folio'].browse(int(active_id))
			reservation_id = folio_id.reservation_id
			domain = []
			if self.transfer_type == 'same_type':
				domain += [('room_categ_id','=',self.old_room_id.room_categ_id.id)]
			hotel_room_ids = self.env["hotel.room"].search(domain)
			hotel_room_ids = hotel_room_ids.filtered(lambda x: x.isroom == True)
			room_ids = []
			for room in hotel_room_ids:
				assigned = False
				for line in room.room_reservation_line_ids.filtered(
						lambda l: l.status != "cancel"
				):
					if reservation_id.checkin and line.check_in and reservation_id.checkout:
						if (
								reservation_id.checkin <= line.check_in <= reservation_id.checkout
						) or (
								reservation_id.checkin <= line.check_out <= reservation_id.checkout
						):
							assigned = True
						elif (line.check_in <= reservation_id.checkin <= line.check_out) or (
								line.check_in <= reservation_id.checkout <= line.check_out
						):
							assigned = True
				for rm_line in room.room_reservation_line_ids.filtered(lambda l: l.status != "cancel"):
					if reservation_id.checkin and rm_line.check_in and reservation_id.checkout:
						if (
								reservation_id.checkin
								<= rm_line.check_in
								<= reservation_id.checkout
						) or (
								reservation_id.checkin
								<= rm_line.check_out
								<= reservation_id.checkout
						):
							assigned = True
						elif (
								rm_line.check_in <= reservation_id.checkin <= rm_line.check_out
						) or (
								rm_line.check_in <= reservation_id.checkout <= rm_line.check_out
						):
							assigned = True
				if not assigned:
					if room.id != self.old_room_id.id:
						room_ids.append(room.id)
			rec.available_room_ids = room_ids

	def action_confirm(self):
		active_id = self._context.get('active_id')
		folio_id = self.env['hotel.folio'].browse(int(active_id))
		folio_id.room_close_id = self.new_room_id.id
		if folio_id.blocking_line:
			folio_id.blocking_line.room_id = self.new_room_id.id
			reservation_line = folio_id.blocking_line.reservation_line
			reservation_line.reserve = [(3,self.old_room_id.id)]
			reservation_line.reserve = [(4,self.new_room_id.id)]