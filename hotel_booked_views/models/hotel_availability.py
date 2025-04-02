# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class HotelAvailability(models.Model):
    _name = "hotel.availability"

    def _get_default_date():
        return fields.Date.today() - relativedelta(days=1)

    def _get_default_to_date():
        return fields.Date.today() + relativedelta(days=3)

    name = fields.Char("Booked", default="Hotel Booked Chart")
    html_body = fields.Html("HTMl BODY", compute="compute_html_body")
    room_type_ids = fields.Many2many("hotel.room.type", string="Room Type")
    from_date = fields.Date("From Date", default=_get_default_date())
    to_date = fields.Date("To Date", default=_get_default_to_date())

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

    @api.onchange("from_date", "to_date")
    def onchange_html_body(self):
        for rec in self:
            rec.html_body = rec.get_html_view()

    def group_by_view(self):
        room_type_ids = self.env["hotel.room.type"].search([]).ids
        room_list = []
        maxlen = 6
        for i in range(0, len(room_type_ids), maxlen):
            room_list.append(room_type_ids[i : i + maxlen])
        return room_list

    def get_list_of_date(self):
        date_list = []
        curr_date = self.from_date or fields.Date.today() - relativedelta(days=1)
        end_date = self.to_date or fields.Date.today() + relativedelta(days=3)
        while curr_date <= end_date:
            date_list.append(curr_date)
            curr_date += relativedelta(days=1)
        return date_list

    def get_html_view(self):
        RoomObj = self.env["hotel.room"]
        ReservationObj = self.env["hotel.reservation"]

        RoomTypeObj = self.env["hotel.room.type"]
        RoomTypeDic = {}
        for t in RoomTypeObj.search([]):
            RoomTypeDic.update({t.id: []})

        bookings_ids = ReservationObj.search(
            [
                ("checkin", ">=", self.from_date),
                ("checkin", "<=", self.to_date),
                ("state", "in", ["confirm", "done"]),
            ]
        )

        checkin = ReservationObj.search(
            [
                ("checkin", ">=", self.from_date),
                ("checkin", "<=", self.to_date),
                ("state", "in", ["confirm", "done"]),
            ]
        )
        checkout = ReservationObj.search(
            [
                ("checkout", ">=", self.from_date),
                ("checkout", "<=", self.to_date),
                ("state", "in", ["confirm", "done"]),
            ]
        )

        for c in checkin:
            for i in c.reservation_line:
                for rev in i.reserve:
                    count_room = RoomTypeDic.get(rev.room_categ_id.id)
                    count_room.append(rev.id)
                    RoomTypeDic.update({rev.room_categ_id.id: count_room})

        # for c in checkout:
        # 	for i in c.reservation_line:
        # 		for rev in i.reserve:
        # 			count_room = RoomTypeDic.get(rev.room_categ_id.id)
        # 			count_room.append(rev.id)
        # 			RoomTypeDic.update({rev.room_categ_id.id:count_room})

        Days = (self.to_date - self.from_date).days + 1

        reservation_line = bookings_ids.reservation_line
        booked_rooms = []
        for rom in reservation_line:
            booked_rooms += rom.reserve.ids
            for rev in rom.reserve:
                count_room = RoomTypeDic.get(rev.room_categ_id.id)
                count_room.append(rev.id)
                RoomTypeDic.update({rev.room_categ_id.id: count_room})

        # for RoomType in RoomTypeDic:
        # 	Rooms = []
        # 	room_type_id = self.env['hotel.room.type'].browse(RoomType)
        # 	Rooms.extend(RoomTypeDic.get(room_type_id.id))
        # 	for child_id in room_type_id.child_ids:
        # 		Rooms.extend(RoomTypeDic.get(child_id.id))
        # 	RoomTypeDic[RoomType] = Rooms

        PerRoom = RoomObj.search_count([])
        allroom = PerRoom
        outoforder = RoomObj.search_count([("is_out_order", "=", True)])  # Days *

        Ready_to_Sale = (
            (allroom - len(booked_rooms) - len(checkin)) + len(checkout)
        ) - outoforder

        # Ready_to_Sale = ((((allroom - len(booked_rooms)) - (len(checkin)+len(checkout)))) - outoforder)
        string = """<tr class="td-header-availability">
							<th class="th-title">Available</th>
							<th class="th-title">Out of order</th>
							<th class="th-title">Expected Arrivals</th>
							<th class="th-title">Expected Departues</th>
							<th class="th-title">Current Occupied</th>
							<th>Ready to sale</th>
						</tr>
						<tr>
							<td class="td-value">{available}</td>
							<td class="td-value">{outoforder}</td>
							<td class="td-value">{checkin}</td>
							<td class="td-value">{checkout}</td>
							<td class="td-value">{occroom}</td>
							<td class="td-value">{readytosale}</td>
					</tr>
				""".format(
            perday=PerRoom,
            available=allroom,
            outoforder=outoforder,
            checkin=len(checkin),
            checkout=len(checkout),
            occroom=len(booked_rooms),
            readytosale=Ready_to_Sale,
        )

        # Remove Code  : May be in Future Need
        # <td class="td-value"><p style="line-height: 1.5;">{available} <span style="color: #6cc1ed;font-size: 11px;"><br/>Per Day {perday} * Days</span></p></td>
        room_body = (
            "<tr><td class='ds-part-type' colspan='6'>Room Type Availability</td></tr>"
        )
        Groups = self.group_by_view()
        for Group in Groups:
            room_body += "<tr class='td-header-availability'>"
            room_body_value = "<tr>"
            for r in Group:
                RoomTypeObj = self.env["hotel.room.type"].browse(r)
                room_booked_count = RoomTypeDic.get(r)
                room_booked_count = list(set(room_booked_count))
                # Rooms = RoomObj.search(['|',('room_categ_id','=',RoomTypeObj.id),('room_categ_id','in',RoomTypeObj.child_ids.ids)])
                # Rooms = Rooms.filtered(lambda x:x.is_out_order == False)
                Rooms = RoomObj.search([("room_categ_id", "=", RoomTypeObj.id)])

                room_body += """<th>{name}</th>""".format(name=RoomTypeObj.name)

                room_body_value += """<td class="td-value">{rooms}</td>""".format(
                    rooms=len(Rooms) - len(room_booked_count)
                )
            room_body_value += "</tr>"
            room_body += "</tr>"
            room_body += room_body_value
        body_html = "<table class='custom-table'>" + string + room_body + "</table>"
        return body_html

    @api.depends("from_date", "to_date")
    def compute_html_body(self):
        for rec in self:
            rec.html_body = rec.get_html_view()
