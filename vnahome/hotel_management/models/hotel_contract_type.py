from odoo import api, fields, models, _


class VNAHotelContractType(models.Model):
    _name = 'hotel.contract.type'

    name = fields.Char(string='Tên')