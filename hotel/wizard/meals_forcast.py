# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _
import datetime
from itertools import groupby
from dateutil.relativedelta import relativedelta

class MealsForcast(models.TransientModel):
    _name = "meals.forcast"
    _description = "Meals Forcast"

    date_start = fields.Date("Start Date")
    date_end = fields.Date("End Date")

    def print_report(self):
        datas = {'active_ids':self.id}
        return self.env.ref('hotel.meals_forcast_report').report_action({},data=datas)

class MealsForcastReport(models.AbstractModel):
    _name = 'report.hotel.report_meals_forcast'
    _description = 'report.hotel.report_meals_forcast'

    @api.model
    def _get_report_values(self,docids,data=None):
        
        active_record = self.env['meals.forcast'].browse(int(data.get('active_ids')))
        date_start = active_record.date_start
        date_end = active_record.date_end

        def get_list_of_date():
            date_list = []
            curr_date = date_start or fields.Date.today() - relativedelta(days=1)
            end_date = date_end or fields.Date.today() + relativedelta(days=3)
            while curr_date <= end_date:
                date_list.append(curr_date)
                curr_date += relativedelta(days=1)
            return date_list
        
        def get_services_data(date):
            
            start_of_today = datetime.datetime.combine(date, datetime.time(00, 00, 00))
            end_of_today = datetime.datetime.combine(date, datetime.time(23, 59, 59))
            print ("\n\n\n\n ****************************************")
            print ("Start Date : -",start_of_today, end_of_today)
            reservations_ids = self.env['hotel.reservation'].search([('checkin','<=',date),('checkout','>=',date),('state','in',('confirm','done'))])

            print ("reservations_ids",reservations_ids)

            services = {}
            service_lines = self.env['hotel.service.line']
            total_rooms = 0
            for reservation in reservations_ids:
                service_lines += reservation.service_line_ids
                total_rooms += len(reservation.reservation_line)
            for service_line in service_lines:
                if services.get(service_line.product_id):
                    services.update({service_line.product_id:services.get(service_line.product_id) + 1})
                else:
                    services.update({service_line.product_id:1})
            return {'services':services,'total_rooms':total_rooms}

        return {
            'docs': docids,
            'get_list_of_date': get_list_of_date,
            'get_services_data': get_services_data,
            'active_record':active_record,
        }