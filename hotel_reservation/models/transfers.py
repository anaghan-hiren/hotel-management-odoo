# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _

class RoomTransfers(models.Model):
	_name = "room.transfers"
	_description = "Room Transfers"

	name = fields.Char('Name')
	html_body = fields.Html('HTML',compute="compute_on_html_body")
	date_from = fields.Date('From Date')
	date_to = fields.Date('To Date')
	reservation_ids = fields.Many2many('hotel.reservation','rel_room_transfers_reservation_id','transfers_id','reservations_id','Reservations')

	def print_pdf_repot(self):
		return self.env.ref('hotel_reservation.action_report_room_transfers').report_action(self)

	@api.depends('date_from','date_to','reservation_ids')
	def compute_on_html_body(self):
		for rec in self:
			rec.html_body = self.get_html_view()

	def get_html_view(self):
		for rec in self:
			main_string = ""
			main_string += """
				<html>
					<div>
						<table class="table">
							<tr>
								<th>From</th>
								<th>To</th>
								<th>Date</th>
								<th>Reason</th>
							</tr>
			"""

			domain = []
			if self.reservation_ids:
				domain += [('reservation_id','in',self.reservation_ids.ids)]
			if self.date_from:
				domain += [('date_transfer','>=',self.date_from)]
			if self.date_to:
				domain += [('date_transfer','<=',self.date_to)]
			transfers_ids = self.env['transfer.request.wizard'].search(domain)
			for transfers_id in transfers_ids:
				main_string += """
					<tr>
						<td>%s</td>
						<td>%s</td>
						<td>%s</td>
						<td>%s</td>
					</tr>
				""" % (transfers_id.old_room_id.name,transfers_id.new_room_id.name,transfers_id.date_transfer.strftime("%d-%m-%Y") if transfers_id.date_transfer else "-",transfers_id.reason)

			main_string += "</table></div></html>"
			return main_string 