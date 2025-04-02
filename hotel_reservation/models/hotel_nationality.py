from odoo import api, fields, models

class OartnerNatinality(models.Model):
    _name = 'res.partner.nationality'
    _rec_name = 'name'
    _description = 'New Description'

    name = fields.Char(required=True)
