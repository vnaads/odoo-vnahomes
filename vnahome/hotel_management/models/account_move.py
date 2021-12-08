from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    room_id = fields.Many2one('hotel.room', string=_('Room'))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    room_id = fields.Many2one('hotel.room', string=_('Room'))

    @api.one
    def _prepare_analytic_line(self):
        res = super(AccountMoveLine, self)._prepare_analytic_line()
        res[0].update({
            'room_id': self.room_id.id or False,
        })
        return res