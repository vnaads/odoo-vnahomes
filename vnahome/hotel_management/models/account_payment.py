from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    room_id = fields.Many2one('hotel.room', string=_('Room'))
    room_categ_id = fields.Many2one('hotel.room.type', string=_("Room Type"), related='room_id.categ_id', store=True)
    folio_id = fields.Many2one('hotel.folio', string=_('Hotel Folio'))
