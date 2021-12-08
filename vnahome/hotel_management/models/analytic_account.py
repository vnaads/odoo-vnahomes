from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class VNAAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    # @api.muli
    # def name_search(self, name='', args=None, operator='ilike', limit=100):
    #     if self.env.context.get('vna_show_aag') == True:
    #         sql = """select spw.id from z_picking_wave_picking hss
    #                 left join z_manifest spw on spw.id = hss.picking_wave
    #                 left join stock_picking sp on sp.id = hss.stock_picking
    #                 where sp.id = %s""" % self.env.context.get('picking_id')
    #         self._cr.execute(sql)
    #         result = self._cr.fetchall()
    #         list_picking_wave = [val for sublist in result for val in sublist]
    #         args += [('id', 'in', list_picking_wave)]
    #     res = super(VNAAnalyticAccount, self).name_search(name, args, operator, limit)
    #     return res

    @api.multi
    def name_get(self):
        res = []
        for r in self:
            if r._context.get('params') and r._context.get('params').get('model') == 'account.invoice':
                name = (r.name or '') + ' (' + (r.group_id.name or '') + ')'
                res.append((r.id, name))
                return res
            else:
                res = super(VNAAnalyticAccount, self).name_get()
                return res


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    folio_id = fields.Many2one('hotel.folio')
    room_id = fields.Many2one('hotel.room', string=_('Room'))
    start_electricity_number = fields.Float(string=_('Số điện bắt đầu'), digits=0, required=True, default=0)
    end_electricity_number = fields.Float(string=_('Số điện kết thúc'), digits=0, required=True, default=0)
    total_electricity_number_consumed = fields.Float(string=_('Kết quả điện sử dụng'), digits=0, required=True,
                                                     default=0,
                                                     compute='get_total_electricity_number', store=True)

    @api.multi
    @api.depends('start_electricity_number', 'end_electricity_number')
    def get_total_electricity_number(self):
        for r in self:
            r.total_electricity_number_consumed = (r.end_electricity_number or 0) - (r.start_electricity_number or 0)

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if self._context.get('folio_id'):
            folio = self.env['hotel.folio'].browse(self._context['folio_id'])
            res.update({'folio_id': folio.id})
            folio.write({'invoice_status': 'invoiced'})
        return res

    @api.multi
    @api.onchange('end_electricity_number')
    def onchange_end_electricity_number(self):
        for r in self:
            if r.end_electricity_number:
                for line in r.invoice_line_ids:
                    if line.is_electric_type:
                        line.quantity = r.end_electricity_number

    # @api.multi
    # @api.constrains('start_electricity_number', 'end_electricity_number')
    # def _check_electricity_number(self):
    #     for account in self:
    #         if account.start_electricity_number > account.end_electricity_number:
    #             raise ValidationError(_(
    #                 'You cannot input start electricity number greater than end electricity number'))

    @api.multi
    def write(self, vals):
        if ('start_electricity_number' in vals or 'end_electricity_number' in vals) and self.invoice_line_ids:
            for line in self.invoice_line_ids:
                if line.product_id.is_electric_type:
                    if 'start_electricity_number' in vals and 'end_electricity_number' in vals:
                        line.quantity = (vals['end_electricity_number'] or 0) - (vals['start_electricity_number'] or 0)
                    if 'start_electricity_number' in vals and 'end_electricity_number' not in vals:
                        line.quantity = (self.end_electricity_number or 0) - (vals['start_electricity_number'] or 0)
                    if 'start_electricity_number' not in vals and 'end_electricity_number' in vals:
                        line.quantity = (vals['end_electricity_number'] or 0) - (self.start_electricity_number or 0)
        result = super(AccountInvoice, self).write(vals)
        return result

    @api.model
    def invoice_line_move_line_get(self):
        res = []
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if line.quantity == 0:
                continue
            tax_ids = []
            for tax in line.invoice_line_tax_ids:
                tax_ids.append((4, tax.id, None))
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        tax_ids.append((4, child.id, None))
            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

            move_line_dict = {
                'invl_id': line.id,
                'type': 'src',
                'name': line.name,
                'price_unit': line.price_unit,
                'quantity': line.quantity,
                'price': line.price_subtotal,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id,
                'room_id': line.room_id.id,
                'uom_id': line.uom_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'analytic_tag_ids': analytic_tag_ids,
                'tax_ids': tax_ids,
                'invoice_id': self.id,
            }
            res.append(move_line_dict)
        return res

    @api.model
    def line_get_convert(self, line, part):
        res = super(AccountInvoice, self).line_get_convert(line, part)
        res.update({
            'room_id': line.get('room_id', False),
        })
        return res

    def action_open_payment_form(self):
        self.ensure_one()
        invoice_id = self.id
        room_id = False
        for r in self.invoice_line_ids:
            if r.room_id:
                room_id = r.room_id
        return {
            'name': _('Invoice Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'no_destroy': True,
            'target': 'new',
            'view_id': self.env.ref('account.view_account_payment_invoice_form') and self.env.ref(
                'account.view_account_payment_invoice_form').id or False,
            'context': {'default_partner_id': self.partner_id.id, 'default_room_id': room_id.id if room_id else False,
                        'default_folio_id': self.folio_id.id if self.folio_id else False,
                        'default_invoice_ids': [(4, invoice_id, None)], 'default_payment_type': 'inbound',
                        'default_room_categ_id': room_id.categ_id.id if room_id and room_id.categ_id else False}
        }


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', store=True, string='Khách hàng')
    invoice_name = fields.Char(string='Số hóa đơn', related='invoice_id.number', store=True)
    account_analytic_group = fields.Many2one('account.analytic.group', string='Analytic Account Group')
    room_id = fields.Many2one('hotel.room', string=_('Room'))
    room_categ_id = fields.Many2one('hotel.room.type', string=_('Room Type'), related='room_id.categ_id', store=True)
    state = fields.Selection(related='invoice_id.state', store=True)

    @api.multi
    @api.onchange('account_analytic_id')
    def onchange_aa(self):
        for r in self:
            if r.account_analytic_id:
                r.account_analytic_group = r.account_analytic_id.group_id

    @api.onchange('room_id')
    def onchange_room_id(self):
        for r in self:
            if r.room_id:
                room_product = self.env['product.product'].search([('id', '=', r.room_id.product_id.id)])
                r.product_id = room_product.id
                r.account_analytic_id = r.room_id.analytic_account_id.id
                r.account_analytic_group = r.room_id.analytic_account_id.group_id.id
