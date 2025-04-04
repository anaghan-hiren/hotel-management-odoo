# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.osv import expression


class HotelServices(models.Model):
    _name = "hotel.services"
    _description = "Hotel Services and its charges"

    product_id = fields.Many2one(
        "product.product",
        "Service_id",
        ondelete="cascade",
        delegate=True,
    )
    service_categ_id = fields.Many2one(
        "hotel.service.type",
        "Service Category",
        required=True,
        ondelete="restrict",
    )
    product_manager = fields.Many2one("res.users")

    @api.model
    def create(self, vals):
        if "service_categ_id" in vals:
            service_categ = self.env["hotel.service.type"].browse(
                vals.get("service_categ_id")
            )
            vals.update({"categ_id": service_categ.product_categ_id.id})
        return super(HotelServices, self).create(vals)

    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        if "service_categ_id" in vals:
            service_categ_id = self.env["hotel.service.type"].browse(
                vals.get("service_categ_id")
            )
            vals.update({"categ_id": service_categ_id.product_categ_id.id})
        return super(HotelServices, self).write(vals)
    
    def action_button_show_product(self):
        xml_id = 'product.product_normal_form_view'
        form_view_id = self.env.ref(xml_id).id
        return {
            'name': _('Product'),
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(form_view_id, 'form')],
            'res_model': 'product.product',
            'res_id': self.product_variant_id.id,
            'type': 'ir.actions.act_window',
        }


class HotelServiceType(models.Model):

    _name = "hotel.service.type"
    _description = "Service Type"

    service_id = fields.Many2one("hotel.service.type", "Service Category")
    child_ids = fields.One2many(
        "hotel.service.type", "service_id", "Service Child Categories"
    )
    product_categ_id = fields.Many2one(
        "product.category",
        "Product Category",
        delegate=True,
        required=True,
        copy=False,
        ondelete="restrict",
    )

    @api.model
    def create(self, vals):
        if "service_id" in vals:
            service_categ = self.env["hotel.service.type"].browse(
                vals.get("service_id")
            )
            vals.update({"parent_id": service_categ.product_categ_id.id})
        return super(HotelServiceType, self).create(vals)

    def write(self, vals):
        if "service_id" in vals:
            service_categ = self.env["hotel.service.type"].browse(
                vals.get("service_id")
            )
            vals.update({"parent_id": service_categ.product_categ_id.id})
        return super(HotelServiceType, self).write(vals)

    def name_get(self):
        def get_names(cat):
            """Return the list [cat.name, cat.service_id.name, ...]"""
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.service_id
            return res

        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            category_names = name.split(" / ")
            parents = list(category_names)
            child = parents.pop()
            domain = [("name", operator, child)]
            if parents:
                names_ids = self.name_search(
                    " / ".join(parents),
                    args=args,
                    operator="ilike",
                    limit=limit,
                )
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([("id", "not in", category_ids)])
                    domain = expression.OR(
                        [[("service_id", "in", categories.ids)], domain]
                    )
                else:
                    domain = expression.AND(
                        [[("service_id", "in", category_ids)], domain]
                    )
                for i in range(1, len(category_names)):
                    domain = [
                        [
                            (
                                "name",
                                operator,
                                " / ".join(category_names[-1 - i :]),
                            )
                        ],
                        domain,
                    ]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]), limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()

