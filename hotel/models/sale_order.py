# Copyright (C) 2022-TODAY Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools, _
from odoo.fields import Command

class SaleOrder(models.Model):
    _inherit = "sale.order"

    booking_line = fields.One2many('sale.order.line','booked_id',string='Booking Line')
    amount_untaxed = fields.Monetary(string="Untaxed Amount", store=True, compute='_compute_amounts', tracking=5)
    amount_tax = fields.Monetary(string="Taxes", store=True, compute='_compute_amounts')
    amount_total = fields.Monetary(string="Total", store=True, compute='_compute_amounts', tracking=4)

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order._compute_lines()
            order_lines = order.order_line.filtered(lambda x: not x.display_type and  not x.product_id.type_of_service == 'free')
            print ("order_lines",order_lines)
            order.amount_untaxed = sum(order_lines.mapped('price_subtotal'))
            order.amount_tax = sum(order_lines.mapped('price_tax'))
            order.amount_total = order.amount_untaxed + order.amount_tax

   # @api.depends('order_line','order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_lines(self):
        """Compute the total amounts of the SO."""
        for order in self:
            follo = self.env['hotel.folio'].search([('order_id','=',order.id)])
            if follo and follo.room_line_ids:
                order.booking_line.unlink()
                lines = []
                ServicePrice = 0
                for s in follo.service_line_ids:
                    vals = {'name':s.name,
                            'booked_id':order.id,
                            'product_id':s.product_id.id,
                            'product_uom':s.product_uom.id,
                            'product_uom_qty':s.product_uom_qty,
                            'tax_id':[(6,0,s.tax_id.ids)],
                            'company_id':s.company_id.id,
                            'currency_id':s.currency_id.id,
                            'price_unit':s.price_unit}
                    taxes = s.tax_id.compute_all(s.price_unit, s.currency_id, s.product_uom_qty, product=s.product_id, partner=False)
                    price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                    ServicePrice += (s.price_unit + price_tax)
                    lines.append(vals)

                PerRoom = ServicePrice/len(follo.room_line_ids.ids)
                for r in follo.room_line_ids:
                    vals = {'name':r.name,
                            'product_id':r.product_id.id,
                            'booked_id':order.id,
                            'product_uom':r.product_uom.id,
                            'tax_id':[(6,0,r.tax_id.ids)],
                            'product_uom_qty':r.product_uom_qty,
                            'company_id':r.company_id.id,
                            'currency_id':r.currency_id.id,
                            'price_unit':r.price_unit-PerRoom}
                    lines.append(vals)
                print ("lineslineslines",lines)
                order.booking_line = [(0,0, v) for v in lines]
            else:
                order.booking_line = False

    #Inherot For Invoice Making Seprate 
    def _get_invoiceable_lines(self, final=False):
        follo = self.env['hotel.folio'].search([('order_id','=',self.id)])
        if follo:
            invoiceable_line_ids = []
            for line in self.booking_line:
                invoiceable_line_ids.append(line.id)
            return self.env['sale.order.line'].browse(invoiceable_line_ids)
        else:
            return super(SaleOrder, self)._get_invoiceable_lines(final=final)
    
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        if self:
            return super(SaleOrder, self.with_context(mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    booked_id = fields.Many2one('sale.order','Booked ID')
    order_id = fields.Many2one(
        comodel_name='sale.order',
        string="Order Reference",
        required=False, ondelete='cascade', index=True, copy=False)


    def _prepare_invoice_line(self, **optional_values):
        if self.booked_id:
            self.ensure_one()
            res = {
                #'display_type': self.display_type or 'product',
                #'sequence': self.sequence,
                'name': self.name,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom.id,
                'quantity': self.product_uom_qty,
                'discount': self.discount,
                'price_unit': self.price_unit,
                'tax_ids': [Command.set(self.tax_id.ids)],
                'sale_line_ids': [Command.link(self.id)],
                'currency_id':self.currency_id.id if self.currency_id else self.env.user.company_id.currency_id.id,
                'company_id':self.company_id.id if self.company_id else self.env.user.company_id.id,
            }
            if self.display_type:
                res['account_id'] = False
            print ("res",res)
            return res
        else:
            return super(SaleOrderLine, self)._prepare_invoice_line(optional_values=optional_values)
       
    @api.depends('invoice_lines', 'invoice_lines.price_total', 'invoice_lines.move_id.state', 'invoice_lines.move_id.move_type')
    def _compute_untaxed_amount_invoiced(self):
        for line in self:
            if line.booked_id:
                amount_invoiced = 0.0
                for invoice_line in line._get_invoice_lines():
                    if invoice_line.move_id.state == 'posted':
                        invoice_date = invoice_line.move_id.invoice_date or fields.Date.today()
                        print ("\n\n  ===line.currency_id, line.company_id,",line.currency_id, line.company_id, invoice_line.currency_id)
                        if invoice_line.move_id.move_type == 'out_invoice':
                            amount_invoiced += invoice_line.price_subtotal
                        elif invoice_line.move_id.move_type == 'out_refund':
                            amount_invoiced -= invoice_line.price_subtotal
                line.untaxed_amount_invoiced = amount_invoiced
            else:
                super(SaleOrderLine, self)._compute_untaxed_amount_invoiced()
    
    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id.get_fiscal_position(line.order_partner_id.id)
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == line.env.company)
            if not line.product_id.isroom:
                line.tax_id = fpos.map_tax(taxes)
