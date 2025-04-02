# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class Booked(models.Model):
    _name = "booked.booked"

    def _get_default_date():
        return fields.Date.today() - relativedelta(days=1)

    def _get_default_to_date():
        return fields.Date.today() + relativedelta(days=3)

    name = fields.Char(
        "Booked",
        default="Hotel Booked Chart",
    )
    html_body = fields.Html(
        "HTMl BODY",
        compute="compute_html_body",
    )
    room_type_ids = fields.Many2many(
        "hotel.room.type",
        string="Room Type",
    )
    from_date = fields.Date(
        "From Date",
        default=_get_default_date(),
    )
    to_date = fields.Date(
        "To Date",
        default=_get_default_to_date(),
    )

    @api.onchange("from_date", "to_date")
    def _onchange_date_range(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            self.from_date = self.to_date
            return {
                "warning": {
                    "title": "Invalid date range",
                    "message": "From date can't be later than To date.",
                }
            }

    def get_list_of_date(self):
        date_list = []
        curr_date = self.from_date or fields.Date.today() - relativedelta(days=1)
        end_date = self.to_date or fields.Date.today() + relativedelta(days=3)
        while curr_date <= end_date:
            date_list.append(curr_date)
            curr_date += relativedelta(days=1)
        return date_list

    def group_by_four(self):
        room_type_ids = []
        if self.room_type_ids:
            for room_type in self.room_type_ids:
                room_type_ids.extend(room_type.child_ids.ids)
                room_type_ids.append(room_type._origin.id)
        else:
            room_type_ids = self.env["hotel.room.type"].search([]).ids
        flats = self.env["hotel.room"].search([("room_categ_id", "in", room_type_ids)])
        flats_list = []
        maxlen = 4
        for i in range(0, len(flats), maxlen):
            flats_list.append(flats[i : i + maxlen])
        return flats_list

    # Form Data For RFQ's Compare
    def get_html_view(self):
        Dates = self.get_list_of_date()
        Groups = self.group_by_four()

        data_html = ""
        Room_html = ""
        for date in Dates:
            if date == date.today():
                data_html += (
                    '<td class="headercall">'
                    + str(date.day)
                    + "-"
                    + str(date.strftime("%b"))
                    + "-"
                    + str(date.year)
                    + "(Today)"
                    + "</td>"
                )
            else:
                data_html += (
                    '<td class="headercall">'
                    + str(date.day)
                    + "-"
                    + str(date.strftime("%b"))
                    + "-"
                    + str(date.year)
                    + "</td>"
                )
            td_html = '<table class="roomtd">'
            for g in Groups:
                td_html += "<tr>"
                for x in g:
                    book_id = self.env["hotel.reservation"].search(
                        [
                            ("checkin", "<=", date),
                            ("checkout", ">=", date),
                            ("reservation_line.reserve", "=", x.id),
                        ]
                    )
                    if len(book_id) > 1:
                        BookingName = ""
                        for b in book_id:
                            BookingName += b.reservation_no + ","
                        raise ValidationError(
                            _(
                                "Opps! Sorry Same Date Time ("
                                + str(date)
                                + ") Two Booking Found. Please, Check This Record "
                                + BookingName
                            )
                        )
                    else:
                        if book_id:
                            if book_id.state == "draft":
                                td_html += '<td class="room actioncall inquiry" id="{id}">RO- {name}</td>'.format(
                                    id=book_id.id, name=x.name
                                )
                            elif book_id.state in ("confirm", "done"):
                                td_html += '<td class="room actioncall booked" id="{id}">RO- {name}</td>'.format(
                                    id=book_id.id, name=x.name
                                )
                        else:
                            td_html += '<td class="room actioncall available" id="{id}">RO- {name}</td>'.format(
                                id=x.id, name=x.name
                            )
                td_html += "</tr>"
            td_html += "</table>"
            Room_html += '<td class="roomscall">' + td_html + "</td>"

        Header_html = "<tr>" + data_html + "</tr>"
        Body_html = "<tr>" + Room_html + "</tr>"
        Html_Content = "<table>" + Header_html + Body_html + "</table>"
        return Html_Content

    @api.depends("from_date", "to_date", "room_type_ids")
    def compute_html_body(self):
        for rec in self:
            rec.html_body = rec.get_html_view()
