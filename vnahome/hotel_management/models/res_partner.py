from odoo import api, fields, models, _


class VNAResPartner(models.Model):
    _inherit = 'res.partner'

    identity_card_number = fields.Char(string='CMND/CCCD')
