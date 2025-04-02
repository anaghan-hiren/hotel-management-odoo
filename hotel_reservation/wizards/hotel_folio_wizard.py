# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from datetime import timedelta
import datetime


class HotelReservationWizard(models.TransientModel):
	_name = "hotel.folio.wizard"
	_description = "Allow to generate a reservation"

	date = fields.Datetime("Date", required=True)
	folio_ids = fields.Many2many('hotel.folio',
								 domain="[('state', '=', 'sale'), ('room_line_ids', '!=', False)]")

	# def _set_room_line_object(self, checkin, checkout, room_number, folio_id):
	# 	obj_room_line = {
	# 		'checkin_date': checkin,
	# 		'checkout_date': checkout,
	# 		'product_id': room_number.id,
	# 		'folio_id': folio_id
	#
	# 	}
	# 	create_line = self.env['hotel.folio.line'].sudo().create(obj_room_line)
	# 	return create_line

	def create_room_lines(self):
		if not self.folio_ids:
			domain = [
				('state', 'not in', ['done', 'cancel']),
				('room_line_ids', '!=', False),
			]
			folio_that_matches_conditions = self.env['hotel.folio'].search(domain)
			for folio in folio_that_matches_conditions:
				# for line in folio.room_line_ids.filtered(lambda x: x.checkin_date.date() != self.date.date()):
				for line in folio.room_line_ids.filtered(lambda x: x.checkin_date.date() == self.date.date()):
					checkin_date = self.date + datetime.timedelta(days=1)
					checkout_date = self.date + datetime.timedelta(days=2)
					folio_id = line.folio_id
					reservation_id = folio_id.reservation_id
					blocking_line = folio_id.blocking_line
					room_number = folio_id.room_close_id.product_id if folio_id.room_close_id else False 
					if not room_number:
						room_number = line.product_id
					folio_lines = len(folio_id.room_line_ids)
					price = 0
					if blocking_line.type_of_rate == 'rate_code':
						price = room_number.list_price
					elif blocking_line.type_of_rate == 'manually':
						price = blocking_line.manual_rate_line.rate_code
					else:
						line_number = folio_lines + 1
						if line_number > len(blocking_line.night_rate_line):
							price = blocking_line.night_rate_line[-1].rate_code
						else:
							price = blocking_line.night_rate_line[line_number-1].rate_code
					obj_room_line = {
						'checkin_date': checkin_date,
						'checkout_date': checkout_date,
						'product_id': room_number.id,
						# 'duration': 1,
						'price_unit': price,
						'folio_id': folio_id.id
					}
					check_line = folio_id.room_line_ids.filtered(lambda x: x.checkin_date.date() == checkin_date.date())
					if folio_id.reservation_id.checkin.date() <= checkin_date.date() <= folio_id.reservation_id.checkout.date():
						if check_line:
							check_room = check_line.filtered(lambda r: r.product_id.id == room_number.id)
							if not check_room:
								folio_id.room_line_ids.create(obj_room_line)
							else:
								pass
						else:
							folio_id.room_line_ids.create(obj_room_line)
					else:
						pass

		elif self.folio_ids:
			for folio in self.folio_ids:
				# for line in folio.room_line_ids.filtered(lambda x: x.checkin_date.date() != self.date.date()):
				for line in folio.room_line_ids.filtered(lambda x: x.checkin_date.date() == self.date.date()):
					checkin_date = self.date + datetime.timedelta(days=1)
					checkout_date = self.date + datetime.timedelta(days=2)
					folio_id = line.folio_id
					folio_lines = len(folio_id.room_line_ids)
					reservation_id = folio_id.reservation_id
					blocking_line = folio_id.blocking_line
					room_number = folio_id.room_close_id.product_id if folio_id.room_close_id else False 
					if not room_number:
						room_number = line.product_id
					price = 0
					if blocking_line.type_of_rate == 'rate_code':
						price = room_number.list_price
					elif blocking_line.type_of_rate == 'manually':
						price = blocking_line.manual_rate_line.rate_code
					else:
						line_number = folio_lines + 1
						if line_number > len(blocking_line.night_rate_line):
							price = blocking_line.night_rate_line[-1].rate_code
						else:
							price = blocking_line.night_rate_line[line_number-1].rate_code
					obj_room_line = {
						'checkin_date': checkin_date,
						'checkout_date': checkout_date,
						'product_id': room_number.id,
						# 'duration': 1,
						'price_unit': price,
						'folio_id': folio_id.id
					}
					check_line = folio_id.room_line_ids.filtered(lambda x: x.checkin_date.date() == checkin_date.date())
					if folio_id.reservation_id.checkin.date() <= checkin_date.date() <= folio_id.reservation_id.checkout.date():
						if check_line:
							check_room = check_line.filtered(lambda r: r.product_id.id == room_number.id)
							if not check_room:
								folio_id.room_line_ids.create(obj_room_line)
							else:
								pass
						else:
							folio_id.room_line_ids.create(obj_room_line)
					else:
						pass
