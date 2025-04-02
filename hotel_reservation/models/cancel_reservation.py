# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _

class ConfirmCancelReservation(models.Model):
	_name = "confirm.cancel.reservation"
	_description = "Confirm Cancel Reservation"

	name = fields.Char('Name')
	reservation_ids = fields.Many2many('hotel.reservation','rel_confirm_reservation_id','confirm_id','reservations_id','Reservations',compute="compute_on_reservations")
	
	def print_pdf_repot(self):
		return self.env.ref('hotel_reservation.action_report_confirm_cancel_reservation').report_action(self)

	def compute_on_reservations(self):
		for rec in self:
			reservation_ids = self.env['hotel.reservation'].search([])
			reservation_ids = reservation_ids.filtered(lambda x:abs((x.option_date - x.date_order.date()).days) >= 5 if x.option_date and x.date_order else False)
			rec.reservation_ids = [(6,0,reservation_ids.ids)]

class CancelReservationAnalysis(models.Model):
	_name = "cancel.reservation.analysis"
	_description = "Cancel Reservation Analysis"

	name = fields.Char('Name')
	html_body = fields.Html('HTML',compute="compute_on_html_body")
	date_from = fields.Date('From Date')
	date_to = fields.Date('To Date')
	order_by = fields.Selection([('reservation_no','Reservation No'),('guest_name','Guest Name')],default="reservation_no",string="Order By")
	reason = fields.Selection([('all','All'),('high_rate','High Rate'),('personal_reasons','Personal reasons'),('bad_review','Bad reviews'),('other','Other')],default="all",string="Reason")

	def print_pdf_repot(self):
		return self.env.ref('hotel_reservation.action_report_cancel_reservation').report_action(self)

	@api.depends('date_from','date_to','order_by','reason')
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
								<th>Reservation number</th>
								<th>Guest name</th>
								<th>Reason of cancellation</th>
								<th>Date of cancel</th>
							</tr>
			"""

			domain = [('state','=','cancel')]
			if self.date_from:
				domain += [('cancel_date','>=',self.date_from)]
			if self.date_to:
				domain += [('cancel_date','<=',self.date_to)]
			orderby = "reservation_no"
			if self.order_by == "guest_name":
				orderby = "partner_id"
			if self.reason != "all":
				domain += [('cancel_reason','=',self.reason)]
			reservation_ids = self.env['hotel.reservation'].search(domain,order="%s ASC" % (orderby))
			for reservation_id in reservation_ids:
				main_string += """
					<tr>
						<td>
							<a href="#id=%d&model=hotel.reservation">%s</a>
						</td>
						<td>%s</td>
						<td>%s</td>
						<td>%s</td>
					</tr>
				""" % (reservation_id.id,reservation_id.reservation_no,reservation_id.partner_id.name,reservation_id.other_reason if reservation_id.other_reason else "High Rate",reservation_id.cancel_date.strftime("%d/%m/%Y") if reservation_id.cancel_date else "-")

			main_string += "</table></div></html>"
			return main_string 