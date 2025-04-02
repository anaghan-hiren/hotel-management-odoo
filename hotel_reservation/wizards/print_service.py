from odoo import fields, models, api, _

class PrintService(models.TransientModel):
	_name = "print.service"
	_description = "Print Service"

	folio_id = fields.Many2one("hotel.folio","Folio")
	is_main_guest_use = fields.Boolean("Is Main Guest Use")
	room_person_ids = fields.Many2many("split.reservation.guest.name","rel_print_s_line_room","print_line_id","person_id",string="Guest Name")
	avl_room_person_ids = fields.Many2many("split.reservation.guest.name","rel_print_a_line_room","print_a_line_id","person_a_id",string="Available Guest Name")

	def print_report(self):
		service_line_ids = []
		if self.is_main_guest_use:
			service_line_ids += self.folio_id.service_line_ids.filtered(lambda x:x.is_main_guest_use).ids
		if self.room_person_ids:
			geusts = self.room_person_ids.ids
			service_line_ids += self.folio_id.service_line_ids.filtered(lambda x:any(x.room_person_ids.filtered(lambda y:y.id in geusts))).ids
		if not service_line_ids and not self.is_main_guest_use and not self.room_person_ids:
			service_line_ids = self.folio_id.service_line_ids
			
		return self.env.ref('hotel.report_hotel_services').report_action(self.folio_id,data={'service_line_ids':service_line_ids})

class HotelReport(models.AbstractModel):
	_name = 'report.hotel.report_hotel_folio_services'

	@api.model
	def _get_report_values(self, docids, data=None):
		docs = self.env['hotel.foliodocs'].browse(self.env.context.get('active_id'))
		service_line_ids = data.get('service_line_ids')
		return {
			"service_line_ids":service_line_ids,
			"docs":docs,
		}