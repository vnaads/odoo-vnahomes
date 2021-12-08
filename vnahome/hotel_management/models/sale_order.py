from odoo import api, fields, models, _


class VNASaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(VNASaleOrderLine, self)._prepare_invoice_line(qty)
        room_analytic_account = self.env['hotel.room'].search([('product_id', '=', self.product_id.id)])
        folio = self.env['hotel.folio'].search([('order_id', '=', self.order_id.id)], limit=1)
        service_analytic_account = self.env['hotel.service.line'].search(
            [('product_id', '=', self.product_id.id), ('folio_id', '=', folio.id)])
        if room_analytic_account:
            res.update({'account_analytic_id': room_analytic_account.analytic_account_id.id or False})
            room_analytic_account.write({'isroom': True})
        if service_analytic_account:
            res.update({'account_analytic_id': service_analytic_account.room_id.analytic_account_id.id or False})
            self.product_id.write({'isservice': True})
        return res


# locct stolen from stack over flow to fix base error
class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=', vals.get('res_model')),
                                                      ('res_id', '=', vals.get('res_id')),
                                                      ('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.unlink()
        res = super(Followers, self).create(vals)
        return res
