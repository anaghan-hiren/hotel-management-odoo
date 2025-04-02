# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import get_lang


class FolioRoomLine(models.Model):

    _name = "folio.room.line"
    _description = "Hotel Room Reservation"
    _rec_name = "room_id"

    room_id = fields.Many2one("hotel.room", ondelete="restrict", index=True)
    check_in = fields.Datetime("Check In Date", required=True)
    check_out = fields.Datetime("Check Out Date", required=True)
    folio_id = fields.Many2one("hotel.folio", "Folio Number", ondelete="cascade")
    status = fields.Selection(related="folio_id.state", string="state")


class HotelFolio(models.Model):

    _name = "hotel.folio"
    _description = "hotel folio"
    _rec_name = "order_id"

    def name_get(self):
        res = []
        fname = ""
        for rec in self:
            if rec.order_id:
                fname = str(rec.name)
                res.append((rec.id, fname))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        if args is None:
            args = []
        args += [("name", operator, name)]
        folio = self.search(args, limit=100)
        return folio.name_get()

    @api.model
    def _get_checkin_date(self):
        self._context.get("tz") or self.env.user.partner_id.tz or "UTC"
        checkin_date = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return fields.Datetime.to_string(checkin_date)

    @api.model
    def _get_checkout_date(self):
        self._context.get("tz") or self.env.user.partner_id.tz or "UTC"
        checkout_date = fields.Datetime.context_timestamp(
            self, fields.Datetime.now() + timedelta(days=1)
        )
        return fields.Datetime.to_string(checkout_date)

    name = fields.Char("Folio Number", readonly=True, index=True, default="New")
    order_id = fields.Many2one(
        "sale.order", "Order", delegate=True, required=True, ondelete="cascade"
    )
    checkin_date = fields.Datetime(
        "Check In",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=_get_checkin_date,
    )
    checkout_date = fields.Datetime(
        "Check Out",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=_get_checkout_date,
    )
    room_line_ids = fields.One2many(
        "hotel.folio.line",
        "folio_id",
        readonly=True,
        states={"draft": [("readonly", False)], "sent": [("readonly", False)]},
        help="Hotel room reservation detail.",
    )
    service_line_ids = fields.One2many(
        "hotel.service.line",
        "folio_id",
        readonly=True,
        states={"draft": [("readonly", False)], "sent": [("readonly", False)]},
        help="Hotel services details provided to"
        "Customer and it will included in "
        "the main Invoice.",
    )
    hotel_policy = fields.Selection(
        [
            ("prepaid", "On Booking"),
            ("manual", "On Check In"),
            ("picking", "On Checkout"),
        ],
        default="manual",
        help="Hotel policy for payment that "
        "either the guest has to payment at "
        "booking time or check-in "
        "check-out time.",
    )
    duration = fields.Float(
        "Duration in Days",
        "count from the check-in and check-out date. ",
    )
    hotel_invoice_id = fields.Many2one("account.move", "Invoice", copy=False)
    duration_dummy = fields.Float()
    total_invoices = fields.Integer("Invoices", compute="compute_on_invoices")

    # to print generated barcode
    def action_print_service_line(self):
        return self.env.ref("hotel.report_hotel_services").report_action(self.id)

    def compute_on_invoices(self):
        for rec in self:
            invoice_ids = self.order_id.invoice_ids.ids
            if self.hotel_invoice_id:
                invoice_ids.append(self.hotel_invoice_id.id)
            rec.total_invoices = len(invoice_ids)

    def action_view_invoices(self):
        invoice_ids = self.order_id.invoice_ids.ids
        if self.hotel_invoice_id:
            invoice_ids.append(self.hotel_invoice_id.id)

        xml_id = "account.view_invoice_tree"
        tree_view_id = self.env.ref(xml_id).id
        xml_id = "account.view_move_form"
        form_view_id = self.env.ref(xml_id).id

        return {
            "name": _("Invoices"),
            "view_mode": "tree,form",
            "views": [(tree_view_id, "tree"), (form_view_id, "form")],
            "res_model": "account.move",
            "domain": [("id", "in", invoice_ids)],
            "type": "ir.actions.act_window",
        }

    @api.constrains("room_line_ids")
    def _check_duplicate_folio_room_line(self):
        """
        This method is used to validate the room_lines.
        ------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        """
        for rec in self:
            for product in rec.room_line_ids.mapped("product_id"):
                for line in rec.room_line_ids.filtered(
                    lambda l: l.product_id == product
                ):
                    record = rec.room_line_ids.search(
                        [
                            ("product_id", "=", product.id),
                            ("folio_id", "=", rec.id),
                            ("id", "!=", line.id),
                            ("checkin_date", ">=", line.checkin_date),
                            ("checkout_date", "<=", line.checkout_date),
                        ]
                    )
                    if record:
                        raise ValidationError(
                            _(
                                """Room Duplicate Exceeded!, """
                                """You Cannot Take Same %s Room Twice!"""
                            )
                            % (product.name)
                        )

    def _update_folio_line(self, folio_id):
        folio_room_line_obj = self.env["folio.room.line"]
        hotel_room_obj = self.env["hotel.room"]
        for rec in folio_id:
            for room_rec in rec.room_line_ids:
                room = hotel_room_obj.search(
                    [("product_id", "=", room_rec.product_id.id)]
                )
                room.write({"isroom": False})
                vals = {
                    "room_id": room.id,
                    "check_in": rec.checkin_date,
                    "check_out": rec.checkout_date,
                    "folio_id": rec.id,
                }
                folio_room_line_obj.create(vals)

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel folio.
        """
        if not "service_line_ids" and "folio_id" in vals:
            tmp_room_lines = vals.get("room_line_ids", [])
            vals["order_policy"] = vals.get("hotel_policy", "manual")
            vals.update({"room_line_ids": []})
            folio_id = super(HotelFolio, self).create(vals)
            for line in tmp_room_lines:
                line[2].update({"folio_id": folio_id.id})
            vals.update({"room_line_ids": tmp_room_lines})
            folio_id.write(vals)
        else:
            if not vals:
                vals = {}
            # vals["name"] = self.env["ir.sequence"].next_by_code("hotel.folio")
            vals["duration"] = vals.get("duration", 0.0) or vals.get("duration", 0.0)
            folio_id = super(HotelFolio, self).create(vals)
            self._update_folio_line(folio_id)
        return folio_id

    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        product_obj = self.env["product.product"]
        hotel_room_obj = self.env["hotel.room"]
        folio_room_line_obj = self.env["folio.room.line"]
        for rec in self:
            rooms_list = [res.product_id.id for res in rec.room_line_ids]
            if vals and vals.get("duration", False):
                vals["duration"] = vals.get("duration", 0.0)
            else:
                vals["duration"] = rec.duration
            room_lst = [folio_rec.product_id.id for folio_rec in rec.room_line_ids]
            new_rooms = set(room_lst).difference(set(rooms_list))
            if len(list(new_rooms)) != 0:
                room_list = product_obj.browse(list(new_rooms))
                for rm in room_list:
                    room_obj = hotel_room_obj.search([("product_id", "=", rm.id)])
                    room_obj.write({"isroom": False})
                    vals = {
                        "room_id": room_obj.id,
                        "check_in": rec.checkin_date,
                        "check_out": rec.checkout_date,
                        "folio_id": rec.id,
                    }
                    folio_room_line_obj.create(vals)
            if not len(list(new_rooms)):
                room_list_obj = product_obj.browse(rooms_list)
                for room in room_list_obj:
                    room_obj = hotel_room_obj.search([("product_id", "=", room.id)])
                    room_obj.write({"isroom": False})
                    room_vals = {
                        "room_id": room_obj.id,
                        "check_in": rec.checkin_date,
                        "check_out": rec.checkout_date,
                        "folio_id": rec.id,
                    }
                    folio_romline_rec = folio_room_line_obj.search(
                        [("folio_id", "=", rec.id)]
                    )
                    folio_romline_rec.write(room_vals)
        return super(HotelFolio, self).write(vals)

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel folio as well
        ---------------------------------------------------------------
        @param self: object pointer
        """
        if self.partner_id:
            self.update(
                {
                    "partner_invoice_id": self.partner_id.id,
                    "partner_shipping_id": self.partner_id.id,
                    "pricelist_id": self.partner_id.property_product_pricelist.id,
                }
            )

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        """
        @param self: object pointer
        """
        for rec in self:
            if not rec.order_id:
                raise UserError(_("Order id is not available"))
            for product in rec.room_line_ids.filtered(
                lambda l: l.order_line_id.product_id == product
            ):
                rooms = self.env["hotel.room"].search([("product_id", "=", product.id)])
                rooms.write({"isroom": True, "status": "available"})
            rec.invoice_ids.button_cancel()
            return rec.order_id.action_cancel()

	# Delivery Order View
    def action_view_delivery(self):
        return self.order_id._get_action_view_picking(self.order_id.picking_ids)

	# Folio Confime 
    def action_confirm(self):
        for record in self:
            order = self.order_id
            order.state = "sale"
            if not order.analytic_account_id:
                if order.order_line.filtered(
                    lambda line: line.product_id.invoice_policy == "cost"
                ):
                    order._create_analytic_account()
            config_parameter_obj = self.env["ir.config_parameter"]
            if config_parameter_obj.sudo().get_param("sale.auto_done_setting"):
                self.order_id.action_done()
            record.action_picking_order()

	# Folio : Delivery Order link 
    def action_picking_order(self):
        picking_obj = self.env["stock.picking"]
        pickingTypeObj = self.env["stock.picking.type"]

        picking_out = pickingTypeObj.search(
            [("warehouse_id", "=", self.warehouse_id.id), ("code", "=", "outgoing")],
            limit=1,
        )
        location_id = picking_out.default_location_src_id
        destination_id = False
        if self.partner_id.property_stock_customer:
            destination_id = self.partner_id.property_stock_customer
        if not destination_id:
            raise ValidationError(
                _(
                    """This partner's destination location was not found. Please configure it """
                    """Customer / Guest Name :  %s """
                )
                % (self.partner_id.name)
            )
        lines = self.preper_picking_line(location_id, destination_id)
        pick_id = picking_obj.create(
            {
                "sale_id": self.order_id.id,
                "partner_id": self.partner_id.id,
                "scheduled_date": self.date_order,
                "picking_type_id": picking_out.id,
                "location_id": location_id.id,
                "location_dest_id": destination_id.id,
                "origin": self.reservation_id.reservation_no,
                "move_ids_without_package": lines,
            }
        )
        pick_id.action_confirm()
        for m in pick_id.move_lines:
            m.quantity_done = m.product_uom_qty
        pick_id.button_validate()

    def preper_picking_line(self, location_id, destination_id):
        lits_of_line = []
        for line in self.service_line_ids.filtered(lambda t: t.product_id.sale_ok):
            lits_of_line.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": line.name or line.product_id.name,
                        "product_uom_qty": line.product_uom_qty,
                        "location_id": location_id.id,
                        "product_uom": line.product_id.uom_id.id,
                        "location_dest_id": destination_id.id,
                    },
                )
            )
        return lits_of_line

    def action_cancel_draft(self):
        """
        @param self: object pointer
        """
        order_line_recs = self.env["sale.order.line"].search(
            [("order_id", "in", self.ids), ("state", "=", "cancel")]
        )
        self.write({"state": "draft", "invoice_ids": []})
        order_line_recs.write(
            {
                "invoiced": False,
                "state": "draft",
                "invoice_lines": [(6, 0, [])],
            }
        )


class HotelFolioLine(models.Model):

    _name = "hotel.folio.line"
    _description = "Hotel Folio Line"

    order_line_id = fields.Many2one(
        "sale.order.line",
        "Order Line",
        required=True,
        delegate=True,
        ondelete="cascade",
    )
    folio_id = fields.Many2one("hotel.folio", "Folio", ondelete="cascade")
    checkin_date = fields.Datetime("Check In", required=True)
    checkout_date = fields.Datetime("Check Out", required=True)
    is_reserved = fields.Boolean(help="True when folio line created from Reservation")

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel folio line.
        """
        if "folio_id" in vals:
            folio = self.env["hotel.folio"].browse(vals["folio_id"])
            vals.update({"order_id": folio.order_id.id})
        return super(HotelFolioLine, self).create(vals)

    @api.constrains("checkin_date", "checkout_date")
    def _check_dates(self):
        """
        This method is used to validate the checkin_date and checkout_date.
        -------------------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        """
        if self.checkin_date and self.checkout_date:
            if self.checkin_date >= self.checkout_date:
                raise ValidationError(
                    _(
                        """Room line Check In Date Should be """
                        """less than the Check Out Date!"""
                    )
                )
            if self.folio_id.date_order and self.checkin_date:
                if self.checkin_date.date() < self.folio_id.date_order.date():
                    raise ValidationError(
                        _(
                            """Room line check in date should be """
                            """greater than the current date."""
                        )
                    )

    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        for line in self:
            if line.order_line_id:
                rooms = self.env["hotel.room"].search(
                    [("product_id", "=", line.order_line_id.product_id.id)]
                )
                folio_room_lines = self.env["folio.room.line"].search(
                    [
                        ("folio_id", "=", line.folio_id.id),
                        ("room_id", "in", rooms.ids),
                    ]
                )
                folio_room_lines.unlink()
                rooms.write({"isroom": True, "status": "available"})
                line.order_line_id.unlink()
        return super(HotelFolioLine, self).unlink()

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
        :param obj product: object of current product record
        :parem float qty: total quentity of product
        :param tuple price_and_rule: tuple(price, suitable_rule) coming
        from pricelist computation
        :param obj uom: unit of measure of current order line
        :param integer pricelist_id: pricelist id of sale order"""
        PricelistItem = self.env["product.pricelist.item"]
        field_name = "lst_price"
        currency_id = None
        product_currency = None
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == "without_discount":
                while (
                    pricelist_item.base == "pricelist"
                    and pricelist_item.base_pricelist_id
                    and pricelist_item.base_pricelist_id.discount_policy
                    == "without_discount"
                ):
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(
                        uom=uom.id
                    ).get_product_price_rule(product, qty, self.folio_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == "standard_price":
                field_name = "standard_price"
            if pricelist_item.base == "pricelist" and pricelist_item.base_pricelist_id:
                field_name = "price"
                product = product.with_context(
                    pricelist=pricelist_item.base_pricelist_id.id
                )
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        product_currency = (
            product_currency
            or (product.company_id and product.company_id.currency_id)
            or self.env.user.company_id.currency_id
        )
        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(
                    product_currency, currency_id
                )

        product_uom = self.env.context.get("uom") or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0
        return product[field_name] * uom_factor * cur_factor, currency_id.id

    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        if self.folio_id.pricelist_id.discount_policy == "with_discount":
            return product.with_context(pricelist=self.folio_id.pricelist_id.id).price
        product_context = dict(
            self.env.context,
            partner_id=self.folio_id.partner_id.id,
            date=self.folio_id.date_order,
            uom=self.product_uom.id,
        )
        final_price, rule_id = self.folio_id.pricelist_id.with_context(
            **product_context
        ).get_product_price_rule(
            self.product_id,
            self.product_uom_qty or 1.0,
            self.folio_id.partner_id,
        )
        base_price, currency_id = self.with_context(
            **product_context
        )._get_real_price_currency(
            product,
            rule_id,
            self.product_uom_qty,
            self.product_uom,
            self.folio_id.pricelist_id.id,
        )
        if currency_id != self.folio_id.pricelist_id.currency_id.id:
            base_price = (
                self.env["res.currency"]
                .browse(currency_id)
                .with_context(**product_context)
                .compute(base_price, self.folio_id.pricelist_id.currency_id)
            )
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = (
                line.order_id.fiscal_position_id
                or line.order_id.fiscal_position_id.get_fiscal_position(
                    line.order_partner_id.id
                )
            )
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(
                lambda t: t.company_id == line.env.company
            )
            line.tax_id = False  # fpos.map_tax(taxes)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product_tmpl = self.product_id.product_tmpl_id
        attribute_lines = product_tmpl.valid_product_template_attribute_line_ids
        valid_values = attribute_lines.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals["product_uom"] = self.product_id.uom_id
            vals["product_uom_qty"] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get("product_uom_qty") or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
        )

        vals.update(
            name=self.order_line_id.get_sale_order_line_multiline_description_sale(
                product
            )
        )

        self._compute_tax_id()

        if self.folio_id.pricelist_id and self.folio_id.partner_id:
            vals["price_unit"] = self.env[
                "account.tax"
            ]._fix_tax_included_price_company(
                self._get_display_price(product),
                product.taxes_id,
                self.tax_id,
                self.company_id,
            )
        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != "no-message":
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning["title"] = title
            warning["message"] = message
            result = {"warning": warning}
            if product.sale_line_warn == "block":
                self.product_id = False
        return result

    @api.onchange("checkin_date", "checkout_date")
    def _onchange_checkin_checkout_dates(self):
        """
        When you change checkin_date or checkout_date it will checked it
        and update the qty of hotel folio line
        -----------------------------------------------------------------
        @param self: object pointer
        """

        configured_addition_hours = (
            self.folio_id.warehouse_id.company_id.additional_hours
        )
        myduration = 0
        if self.checkin_date and self.checkout_date:
            dur = self.checkout_date - self.checkin_date
            sec_dur = dur.seconds
            if (not dur.days and not sec_dur) or (dur.days and not sec_dur):
                myduration = dur.days
            else:
                myduration = dur.days + 1
            #            To calculate additional hours in hotel room as per minutes
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60) / 60)
                if additional_hours >= configured_addition_hours:
                    myduration += 1
        self.product_uom_qty = myduration

    def copy_data(self, default=None):
        """
        @param self: object pointer
        @param default: dict of default values to be set
        """

        sale_line_obj = self.order_line_id
        print("order_line_idorder_line_idorder_line_id", order_line_id)
        return sale_line_obj.copy_data(default=default)


class HotelServiceLine(models.Model):

    _name = "hotel.service.line"
    _description = "hotel Service line"

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        """
        @param self: object pointer
        @param default: dict of default values to be set
        """
        return super(HotelServiceLine, self).copy(default=default)

    service_line_id = fields.Many2one(
        "sale.order.line",
        "Service Line",
        required=True,
        delegate=True,
        ondelete="cascade",
    )
    folio_id = fields.Many2one("hotel.folio", "Folio", ondelete="cascade")
    ser_checkin_date = fields.Datetime("From Date")
    ser_checkout_date = fields.Datetime("To Date")

    @api.model
    def create(self, vals):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel service line.
        """
        if "folio_id" in vals:
            folio = self.env["hotel.folio"].browse(vals["folio_id"])
            vals.update({"order_id": folio.order_id.id})
        return super(HotelServiceLine, self).create(vals)

    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        self.mapped("service_line_id").unlink()
        return super().unlink()

    def _compute_tax_id(self):
        for line in self:
            fpos = (
                line.folio_id.fiscal_position_id
                or line.folio_id.partner_id.property_account_position_id
            )
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id
            )
            line.tax_id = (
                fpos.map_tax(taxes, line.product_id, line.folio_id.partner_shipping_id)
                if fpos
                else taxes
            )

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
        :param obj product: object of current product record
        :parem float qty: total quentity of product
        :param tuple price_and_rule: tuple(price, suitable_rule)
        coming from pricelist computation
        :param obj uom: unit of measure of current order line
        :param integer pricelist_id: pricelist id of sale order"""
        PricelistItem = self.env["product.pricelist.item"]
        field_name = "lst_price"
        currency_id = None
        product_currency = None
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == "without_discount":
                while (
                    pricelist_item.base == "pricelist"
                    and pricelist_item.base_pricelist_id
                    and pricelist_item.base_pricelist_id.discount_policy
                    == "without_discount"
                ):
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(
                        uom=uom.id
                    ).get_product_price_rule(product, qty, self.folio_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == "standard_price":
                field_name = "standard_price"
            if pricelist_item.base == "pricelist" and pricelist_item.base_pricelist_id:
                field_name = "price"
                product = product.with_context(
                    pricelist=pricelist_item.base_pricelist_id.id
                )
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        product_currency = (
            product_currency
            or (product.company_id and product.company_id.currency_id)
            or self.env.user.company_id.currency_id
        )
        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(
                    product_currency, currency_id
                )

        product_uom = self.env.context.get("uom") or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0
        return product[field_name] * uom_factor * cur_factor, currency_id.id

    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        if self.folio_id.pricelist_id.discount_policy == "with_discount":
            return product.with_context(pricelist=self.folio_id.pricelist_id.id).price
        product_context = dict(
            self.env.context,
            partner_id=self.folio_id.partner_id.id,
            date=self.folio_id.date_order,
            uom=self.product_uom.id,
        )
        final_price, rule_id = self.folio_id.pricelist_id.with_context(
            **product_context
        ).get_product_price_rule(
            self.product_id,
            self.product_uom_qty or 1.0,
            self.folio_id.partner_id,
        )
        base_price, currency_id = self.with_context(
            **product_context
        )._get_real_price_currency(
            product,
            rule_id,
            self.product_uom_qty,
            self.product_uom,
            self.folio_id.pricelist_id.id,
        )
        if currency_id != self.folio_id.pricelist_id.currency_id.id:
            base_price = (
                self.env["res.currency"]
                .browse(currency_id)
                .with_context(**product_context)
                .compute(base_price, self.folio_id.pricelist_id.currency_id)
            )
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product_tmpl = self.product_id.product_tmpl_id
        attribute_lines = product_tmpl.valid_product_template_attribute_line_ids
        valid_values = attribute_lines.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals["product_uom"] = self.product_id.uom_id
            vals["product_uom_qty"] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get("product_uom_qty") or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
        )

        vals.update(
            name=self.service_line_id.get_sale_order_line_multiline_description_sale(
                product
            )
        )

        self._compute_tax_id()

        if self.folio_id.pricelist_id and self.folio_id.partner_id:
            vals["price_unit"] = self.env[
                "account.tax"
            ]._fix_tax_included_price_company(
                self._get_display_price(product),
                product.taxes_id,
                self.tax_id,
                self.company_id,
            )
        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != "no-message":
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning["title"] = title
            warning["message"] = message
            result = {"warning": warning}
            if product.sale_line_warn == "block":
                self.product_id = False
        return result

    @api.onchange("ser_checkin_date", "ser_checkout_date")
    def _on_change_checkin_checkout_dates(self):
        """
        When you change checkin_date or checkout_date it will checked it
        and update the qty of hotel service line
        -----------------------------------------------------------------
        @param self: object pointer
        """
        if not self.ser_checkin_date:
            time_a = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.ser_checkin_date = time_a
        if not self.ser_checkout_date:
            self.ser_checkout_date = time_a
        if self.ser_checkout_date < self.ser_checkin_date:
            raise ValidationError(_("Checkout must be greater or equal checkin date"))
        if self.ser_checkin_date and self.ser_checkout_date:
            diffDate = self.ser_checkout_date - self.ser_checkin_date
            qty = diffDate.days + 1
            self.product_uom_qty = qty

    def copy_data(self, default=None):
        """
        @param self: object pointer
        @param default: dict of default values to be set
        """
        print("Service Line ", self.service_line_id)
        return self.service_line_id.copy_data(default=default)

    # @api.onchange("product_id","price_unit")
    # def _onchange_product(self):
    #     for r in self:
    #         r.service_line_id.order_id._compute_lines()
