# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
import datetime


class FolioReportWizard(models.TransientModel):
    _name = "folio.report.wizard"
    _rec_name = "date_start"
    _description = "Allow print folio report by date"

    date_start = fields.Date("Start Date")
    date_end = fields.Date("End Date")

    def print_report(self):
        data = {
            "ids": self.ids,
            "model": "hotel.folio",
            "form": self.read(["date_start", "date_end"])[0],
        }
        return self.env.ref("hotel.report_hotel_management").report_action(
            self, data=data
        )

    def print_guest_list_report(self):
        datas = {'active_ids':self.id}
        move_ids = self.env['hotel.folio'].search([])
        return self.env.ref('hotel.report_print_guest_list').report_action(move_ids,data=datas)

class HotelGuestListReport(models.AbstractModel):
    _name = 'report.hotel.report_hotel_guest_list_tmpl'
    _description = 'report.hotel.report_hotel_guest_list_tmpl'

    @api.model
    def _get_report_values(self,docids,data=None):
        active_record = self.env['folio.report.wizard'].browse(int(data.get('active_ids')))
        
        start_of_today = datetime.datetime.combine(active_record.date_start, datetime.time(00, 00, 00))
        end_of_today = datetime.datetime.combine(active_record.date_start, datetime.time(23, 59, 59))
        
        records = self.env['hotel.reservation'].search([('checkin','<=',active_record.date_start),('checkout','>=',active_record.date_start)])
				

       # records = self.env['hotel.reservation'].search([('checkin','>=',start_of_today),('checkout','<=',end_of_today),'|',('checkout','>=',start_of_today),('checkout','<=',end_of_today)])
        print ("recordsrecordsrecords",records)
        # reservations_ids = self.env['hotel.reservation'].search(['|',('checkin','>=',active_record.date_start),('checkout','<=',active_record.date_end),('state','in',('confirm','done'))])
        # print ("\n\n\ ********* ************************************",reservations_ids)
        # for res in reservations_ids:
        #     print ("\n\n\ resresresres == >>> > > > > > >> > . . ",res.name)

        # STOPPPPP
        def get_service_line(folio_id):
            line = self.env['hotel.service.line'].search([('reservation_id','=',folio_id.id),('product_id.type_of_service','=','free')],limit=1)
            return line.name or ''

        
        return {
            'docs': records,
            'get_service_line':get_service_line,
            'active_record':active_record,
        }