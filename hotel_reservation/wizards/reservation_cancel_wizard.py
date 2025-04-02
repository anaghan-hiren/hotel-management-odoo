# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from datetime import timedelta , datetime , date


class ReservationCancel(models.TransientModel):
	_name = "reservation.cancel"
	_description = "Reservation Cancel"

	reason = fields.Selection([('high_rate','High Rate'),('personal_reasons','Personal reasons'),('bad_review','Bad reviews'),('other','Other')],default="high_rate",string="Reason")
	other_reason = fields.Char('Other Reason')

	def action_confirm(self):
		active_id = self._context.get('active_id')
		reservation_id = self.env['hotel.reservation'].browse(int(active_id))
		reservation_id.cancel_reason = self.reason
		other_reason = ""
		if self.reason == "high_rate":
			other_reason = "High Rate"
		if self.reason == "personal_reasons":
			other_reason = "Personal reasons"
		if self.reason == "bad_review":
			other_reason = "Bad reviews"
		if self.reason == "other":
			other_reason = self.other_reason

		reservation_id.other_reason = other_reason
		reservation_id.cancel_date = date.today()
		string = "Reservation Canceled by %s on %s \n Reason :- %s" % (self.env.user.name,date.today().strftime("%d/%m/%Y"),other_reason)
		reservation_id.message_post(body=string)
		reservation_id.cancel_reservation()