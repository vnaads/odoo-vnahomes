# -*- coding: utf-8 -*-
import uuid
from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = "res.users"

    token = fields.Char(string='Token', copy=False)
    # gmo_code = fields.Char(string='GMO code', copy=False)
    #
    # _sql_constraints = [('unique_gmo_code', 'UNIQUE(gmo_code)', "gmo_code must be unique")]

    @api.multi
    def get_user_access_token(self):
        return uuid.uuid4().hex

    @api.multi
    def check_token(self, token, login):
        res = False
        if token:
            user = self.sudo().search([
                ('token', '=', token),
                ('login', '=', login)
            ])
            if user:
                res = user
        return res
