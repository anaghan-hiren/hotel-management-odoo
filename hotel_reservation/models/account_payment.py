# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api

class AccountPayment(models.Model):
	_inherit = "account.payment"

	reservation_id = fields.Many2one("hotel.reservation",string="Reservation")
	folio_id = fields.Many2one("hotel.folio",string="Folio")
	hotel_payment_type = fields.Selection([('room_payment','Room Payment'),('service_payment','Service Payment')],string="Hotel Payment Type")
	is_main_guest_use = fields.Boolean("Is Main Guest Use")
	room_person_ids = fields.Many2many("split.reservation.guest.name","rel_payment_line_room","payment_line_id","person_id",string="Guest Name")	
	blocking_line = fields.Many2one('split.reservation.line','blocking')
	avl_room_person_ids = fields.Many2many("split.reservation.guest.name","rel_payment_a_line_room","payment_a_line_id","person_a_id",string="Available Guest Name")
	service_payment_type = fields.Selection([('all_services','All Services'),('my_services','My Services')],default="all_services",string="Sevice Payment Type")
	is_show_options = fields.Boolean("Is Show Options")

	@api.model
	def default_get(self,fields):
		res = super().default_get(fields)
		if self._context.get("blocking_line"):
			res['blocking_line'] = self._context.get("blocking_line")
			blocking_line = self.env['split.reservation.line'].browse(self._context.get("blocking_line"))
			res['avl_room_person_ids'] = blocking_line.geust_lines
		return res

	@api.onchange("is_main_guest_use","service_payment_type","room_person_ids")
	def onchange_on_amount(self):
		for rec in self:
			total = rec.folio_id.get_totals(rec.is_main_guest_use,rec.room_person_ids.ids,rec.service_payment_type)
			rec.amount = total

	def action_post(self):
		res = super(AccountPayment, self).action_post()
		if self._context.get("reservation_id"):
			folio = self.env["hotel.reservation"].browse(self._context["reservation_id"])
			folio.write({"payment_ids": [(4,self.id)]})
		return res