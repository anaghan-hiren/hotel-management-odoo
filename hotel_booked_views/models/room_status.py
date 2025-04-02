# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from datetime import datetime


class RoomStatus(models.Model):
    _name = "room.status"

    def _get_default_date():
        return fields.Date.today()

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
    from_date = fields.Date("From Date", default=_get_default_date())
    to_date = fields.Date("To Date")
    status = fields.Selection(
        [
            ("all", "All"),
            ("occupied", "Occupied"),
            ("vacant", "Vacant/Available"),
        ],
        string="Status",
        default="all",
    )

    @api.onchange("from_date", "to_date", "status")
    def onchange_html_body(self):
        for rec in self:
            rec.compute_html_body()

    def get_html_view(self):
        domain = []
        # if self.status == 'occupied':
        # 	domain += [('status','=','occupied')]
        Rooms = self.env["hotel.room"].search(domain)
        Room_html = ""
        if self.status == "vacant":
            for r in Rooms:
                book_id = self.env["hotel.reservation"].search(
                    [
                        ("checkin", "<=", self.from_date),
                        ("checkout", ">=", self.from_date),
                        ("reservation_line.reserve", "=", r.id),
                    ]
                )
                if not book_id:
                    class_name = "vacant"
                    Room_html += """
							<div class="room">
									<p class="roomtitle {classname}">{no}</p>
									<div>
										<p>Floor No : -</p>
										<p>Room Type : {type}</p>
										<p>Next Expected Arrival :{checkin}</p>
										<p>Expected Departure : {checkout}</p>
									</div>
								</div>""".format(
                        no=r.name,
                        classname=class_name,
                        type=r.room_categ_id.name,
                        checkin=(
                            book_id.checkin.strftime("%d-%m-%Y %H:%M:%S")
                            if book_id.checkin
                            else ""
                        ),
                        checkout=(
                            book_id.checkout.strftime("%d-%m-%Y %H:%M:%S")
                            if book_id.checkout
                            else ""
                        ),
                    )
        if self.status == "occupied":
            for r in Rooms:
                book_id = self.env["hotel.reservation"].search(
                    [
                        ("checkin", "<=", self.from_date),
                        ("checkout", ">=", self.from_date),
                        ("reservation_line.reserve", "=", r.id),
                    ]
                )
                if len(book_id) > 1:
                    BookingName = ""
                    for b in book_id:
                        BookingName += b.reservation_no + ","
                    raise ValidationError(
                        _(
                            "Opps! Sorry Same Date Time ("
                            + str(self.from_date)
                            + ") Two Booking Found. Please, Check This Record "
                            + BookingName
                        )
                    )
                else:
                    if book_id:
                        class_name = "vacant"
                        Room_html += """
								<div class="room">
										<p class="roomtitle {classname}">{no}</p>
										<div>
											<p>Floor No : -</p>
											<p>Room Type : {type}</p>
											<p>Next Expected Arrival :{checkin}</p>
											<p>Expected Departure : {checkout}</p>
										</div>
									</div>""".format(
                            no=r.name,
                            classname=class_name,
                            type=r.room_categ_id.name,
                            checkin=(
                                book_id.checkin.strftime("%d-%m-%Y %H:%M:%S")
                                if book_id.checkin
                                else ""
                            ),
                            checkout=(
                                book_id.checkout.strftime("%d-%m-%Y %H:%M:%S")
                                if book_id.checkout
                                else ""
                            ),
                        )
        if self.status == "all":
            for r in Rooms:
                book_id = self.env["hotel.reservation"].search(
                    [
                        ("checkin", "<=", self.from_date),
                        ("checkout", ">=", self.from_date),
                        ("reservation_line.reserve", "=", r.id),
                    ]
                )
                if len(book_id) > 1:
                    BookingName = ""
                    for b in book_id:
                        BookingName += b.reservation_no + ","
                    raise ValidationError(
                        _(
                            "Opps! Sorry Same Date Time ("
                            + str(self.from_date)
                            + ") Two Booking Found. Please, Check This Record "
                            + BookingName
                        )
                    )
                else:
                    class_name = "vacant"
                    if r.is_out_order:
                        class_name = "outoforder"
                    if book_id:
                        class_name = "occupied"

                    checkin = ""
                    checkout = ""
                    if book_id.checkin:
                        # BSplit = str(book_id.checkin).split('.')
                        # checkin = BSplit[0]
                        checkin = book_id.checkin.strftime("%d-%m-%Y %H:%M:%S")
                    if book_id.checkout:
                        # BSplit = str(book_id.checkout).split('.')
                        # checkout = BSplit[0]
                        checkout = book_id.checkout.strftime("%d-%m-%Y %H:%M:%S")

                    Room_html += """
							<div class="room">
									<p class="roomtitle {classname}">{no}</p>
									<div>
										<p>Floor No : {floor}</p>
										<p>Room Type : {type}</p>
										<p>Next Expected Arrival :{checkin}</p>
										<p>Expected Departure : {checkout}</p>
									</div>
								</div>""".format(
                        no=r.name,
                        floor=r.floor_id.name or "-",
                        classname=class_name,
                        type=r.room_categ_id.name,
                        checkin=checkin,
                        checkout=checkout,
                    )
        string = """	
					<div class="roomlist">
						{room_html}
					</div>
				""".format(
            room_html=Room_html
        )
        return string

    @api.depends("from_date", "to_date", "room_type_ids", "status")
    def compute_html_body(self):
        for rec in self:
            rec.html_body = rec.get_html_view()
