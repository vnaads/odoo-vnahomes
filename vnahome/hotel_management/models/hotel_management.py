import time
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class VNAHotelRoomTypeInherit(models.Model):
    _inherit = 'hotel.room.type'

    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.user.company_id)
    active = fields.Boolean(default=True, string='Active')

    @api.onchange('active')
    def onchange_active(self):
        for r in self:
            if r.active:
                for room in r.room_ids:
                    room.active = r.active


class VNAHotelRoom(models.Model):
    _inherit = 'hotel.room'

    analytic_account_id = fields.Many2one('account.analytic.account', string=_('Analytic Account'), index=True)
    folio_ids = fields.One2many('hotel.folio', 'room_id', string="Folio")
    folio_count = fields.Integer(string="Hợp đồng", compute='calculate_folio', store=True)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.user.company_id)
    active = fields.Boolean(default=True, string='Active')
    room_status = fields.Selection([
        ('no_ready', 'Chưa sẵn sàng'),
        ('ready', 'Đã sẵn sàng'),
    ], string="Tình trạng phòng", default="ready")
    weekend_price = fields.Float('Weekend Price', digits=dp.get_precision('Product Price'), default=0.0)

    @api.multi
    @api.depends('folio_ids')
    def calculate_folio(self):
        for r in self:
            r.folio_count = len(r.folio_ids)

    @api.multi
    def action_view_folio(self):
        view = self.env.ref('hotel.view_hotel_folio_form')

        action = self.env.ref('hotel.open_hotel_folio1_form_tree_all').read()[0]
        # po_ids = [] #
        # for r in self.sudo().purchase_order_ids:
        # po_ids.append(r.id)
        if len(self.sudo().folio_ids) == 1:
            action['views'] = [(view.id, 'form')]
            action['view_id'] = view.id
            action['res_id'] = self.sudo().folio_ids[0].id
        else:
            action['domain'] = [('id', 'in', self.sudo().folio_ids.ids)]
        return action

    @api.multi
    def name_get(self):
        res = []
        for r in self:
            name = (r.name or '') + ' (' + (r.categ_id.name or '') + ')'
            res.append((r.id, name))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            categ_ids = []
            categ_obj = self.categ_id.search([('name', operator, name)])
            for cate in categ_obj:
                categ_ids.append(cate.id)
            args += (['|', ('name', operator, name), ('categ_id', 'in', categ_ids)])
            room = self.search(args, limit=100)
            return room.name_get()
        else:
            categ_ids = []
            categ_obj = self.categ_id.search([('name', operator, name)])
            for cate in categ_obj:
                categ_ids.append(cate.id)
            args += (['|', ('name', operator, name), ('categ_id', 'in', categ_ids)])
            room = self.search(args, limit=100)
            return room.name_get()

    @api.model
    def create(self, vals):
        res = super(VNAHotelRoom, self).create(vals)
        analytic_group = False
        if res.categ_id:
            analytic_group = res.categ_id.group_id.id
        analytic_val = {
            'name': res.name,
            'group_id': analytic_group
        }
        analytic_obj = self.env['account.analytic.account'].create(analytic_val)
        res.analytic_account_id = analytic_obj.id
        return res

    @api.multi
    def unlink(self):
        for r in self:
            if len(r.room_line_ids) >= 1:
                raise ValidationError(_('Không thể xóa phòng khi đã có phát sinh trong hợp đồng !'))
            product = self.env['product.product'].search([('id', '=', r.product_id.id)], limit=1)
            aa = self.env['account.analytic.account'].search([('id', '=', r.analytic_account_id.id)], limit=1)
            if product:
                product.sudo().unlink()
            if aa:
                aa.sudo().unlink()
            res = super(VNAHotelRoom, self).unlink()
            return res

    @api.onchange('name')
    def onchange_name(self):
        if self.analytic_account_id:
            self.analytic_account_id.write({'name': self.name})

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        if self.categ_id:
            if self.analytic_account_id:
                self.analytic_account_id.write({'group_id': self.categ_id.group_id.id})


class VNAHotelRoomType(models.Model):
    _inherit = 'hotel.room.type'

    group_id = fields.Many2one('account.analytic.group', string=_("Analytic Group"))

    @api.model
    def create(self, vals):
        res = super(VNAHotelRoomType, self).create(vals)
        group_id_val = {
            'name': res.name
        }
        group_obj = self.env['account.analytic.group'].create(group_id_val)
        res.group_id = group_obj.id
        return res

    @api.multi
    def unlink(self):
        for r in self:
            # product = self.env['product.product'].search([('id', '=', r.product_id.id)], limit=1)
            aag = self.env['account.analytic.group'].search([('id', '=', r.group_id.id)], limit=1)
            # if product:
            #     product.sudo().unlink()
            if aag:
                aag.sudo().unlink()
            res = super(VNAHotelRoomType, self).unlink()
            return res

    @api.onchange('name')
    def onchange_name(self):
        if self.group_id:
            self.group_id.write({'name': self.name})


class VNAHotelFolio(models.Model):
    _inherit = 'hotel.folio'
    _order = 'create_date desc'

    product_domain_ids = fields.Many2many('product.product', compute='_compute_product_domain_ids', store=True)
    room_domain_ids = fields.Many2many('hotel.room', compute='_compute_product_domain_ids', store=True)
    folio_invoice_ids = fields.One2many('account.invoice', 'folio_id', string='Invoice', copy=False)
    readonly_field = fields.Boolean(string='Readonly field', default=False)
    expired_date = fields.Integer(string=_('Expired Date'), compute='get_expired_date', store=True)
    room_checkin_date = fields.Datetime(string="Checkin Date", compute='get_check_date', store=True)
    room_checkout_date = fields.Datetime(string="Checkout Date", compute='get_check_date', store=True)
    room_id = fields.Many2one('hotel.room', string=_('Room'), compute='compute_room_id', store=True)
    start_electricity_number = fields.Float(string=_('Số điện bắt đầu'), digits=0, required=True, default=0)
    folio_payment_ids = fields.One2many('account.payment', 'folio_id', string='Payment', copy=False)
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.user.company_id)
    hotel_contract_type_id = fields.Many2one('hotel.contract.type', string='Loại hợp đồng')

    @api.multi
    @api.depends('room_lines.room_id')
    def compute_room_id(self):
        for r in self:
            if r.room_lines:
                r.room_id = r.room_lines[0].room_id.id

    @api.multi
    @api.depends('room_lines.checkin_date', 'room_lines.checkout_date')
    def get_check_date(self):
        for r in self:
            if r.room_lines:
                r.room_checkin_date = r.room_lines[0].checkin_date
                r.room_checkout_date = r.room_lines[0].checkout_date

    @api.multi
    @api.depends('room_lines.checkout_date')
    def get_expired_date(self):
        for r in self:
            if r.room_lines:
                r.expired_date = (r.room_lines[0].checkout_date - datetime.now()).days

    @api.multi
    def action_cancel(self):
        '''
        @param self: object pointer
        '''
        if not self.order_id:
            raise UserError(_('Order id is not available'))
        for sale in self:
            for invoice in sale.folio_invoice_ids:
                invoice.state = 'cancel'
        for line in self.room_lines:
            line.room_id.isroom = True
            line.room_id.product_id.isroom = True
        return self.order_id.action_cancel()

    @api.multi
    @api.depends('room_lines.room_id')
    def _compute_product_domain_ids(self):
        for r in self:
            product_ids = []
            room_ids = []
            if r.room_lines:
                for sale in r.room_lines:
                    product_ids.append(sale.product_id.id)
                    room_ids.append(sale.room_id.id)
                product_domain = self.env['product.product'].search([('id', 'in', product_ids)])
                room_domain = self.env['hotel.room'].search([('id', 'in', room_ids)])
                r.product_domain_ids = [(6, product_ids, product_domain.ids)]
                r.room_domain_ids = [(6, room_ids, room_domain.ids)]

    @api.multi
    def action_done(self):
        for r in self:
            r.state = 'done'
            for line in r.room_lines:
                line.room_id.isroom = True
                line.room_id.product_id.isroom = True

    @api.multi
    def unlink(self):
        for r in self:
            for line in r.room_lines:
                line.room_id.isroom = True
                line.room_id.product_id.isroom = True
            if r.state != 'draft':
                raise ValidationError(_('Không thể xóa hợp đồng ở trạng thái Xác nhận hay Hoàn thành!'))
        return super(VNAHotelFolio, self).unlink()

    @api.multi
    def action_wizzard_invoice(self):
        for r in self:
            return {
                'name': _('Tạo hóa đơn'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.automatic.invoice',
                'view_id': self.env.ref('hotel_management.view_wizard_invoice_form').id,
                'type': 'ir.actions.act_window',
                'context': {
                    'default_folio_id': r.id,
                },
                'target': 'new'
            }

    @api.multi
    def _prepare_invoice(self):
        for r in self:
            company_id = r.company_id.id
            journal_id = (self.env['account.invoice'].with_context(company_id=company_id or self.env.user.company_id.id)
                .default_get(['journal_id'])['journal_id'])
            if not journal_id:
                raise UserError(_('Please define an accounting sales journal for this company.'))
            vinvoice = self.env['account.invoice'].new({'partner_id': r.partner_invoice_id.id})
            # Get partner extra fields
            vinvoice._onchange_partner_id()
            invoice_vals = vinvoice._convert_to_write(vinvoice._cache)
            invoice_vals.update({
                'name': r.client_order_ref or '',
                'origin': r.name,
                'type': 'out_invoice',
                'account_id': r.partner_invoice_id.property_account_receivable_id.id,
                'partner_shipping_id': r.partner_shipping_id.id,
                'journal_id': journal_id,
                'currency_id': r.pricelist_id.currency_id.id,
                'comment': r.note,
                'payment_term_id': r.payment_term_id.id,
                'fiscal_position_id': r.fiscal_position_id.id or r.partner_invoice_id.property_account_position_id.id,
                'company_id': company_id,
                'user_id': r.user_id and r.user_id.id,
                'team_id': r.team_id.id,
                'transaction_ids': [(6, 0, r.transaction_ids.ids)],
                'folio_id': r.id,
                'room_id': r.room_id.id,
            })
            return invoice_vals

    @api.multi
    def action_create_invoice(self, grouped=False, final=False):
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        invoices_origin = {}
        invoices_name = {}

        # Keep track of the sequences of the lines
        # To keep lines under their section
        inv_line_sequence = 0
        for order in self:
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)

            # We only want to create sections that have at least one invoiceable line
            pending_section = None

            # Create lines in batch to avoid performance problems
            line_vals_list = []
            # sequence is the natural order of order_lines
            for line in order.room_lines:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    last_invoice = inv_obj.search([('folio_id', '=', self.id), ('id', '!=', invoice.id)],
                                                  order='id desc', limit=1)
                    if not last_invoice:
                        invoice.start_electricity_number = self.start_electricity_number
                    else:
                        invoice.start_electricity_number = last_invoice.end_electricity_number
                    references[invoice] = order
                    invoices[group_key] = invoice
                    invoices_origin[group_key] = [invoice.origin]
                    invoices_name[group_key] = [invoice.name]
                elif group_key in invoices:
                    if order.name not in invoices_origin[group_key]:
                        invoices_origin[group_key].append(order.name)
                    if order.client_order_ref and order.client_order_ref not in invoices_name[group_key]:
                        invoices_name[group_key].append(order.client_order_ref)

                if line.folio_id:
                    if pending_section:
                        section_invoice = pending_section.invoice_line_create_vals(
                            invoices[group_key].id
                        )
                        inv_line_sequence += 1
                        section_invoice[0]['sequence'] = inv_line_sequence
                        line_vals_list.extend(section_invoice)
                        pending_section = None

                    inv_line_sequence += 1
                    inv_line = line.invoice_line_create_vals(
                        invoices[group_key].id
                    )
                    inv_line[0]['sequence'] = inv_line_sequence
                    line_vals_list.extend(inv_line)

            for service_line in order.service_lines:
                if service_line.display_type == 'line_section':
                    pending_section = service_line
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    last_invoice = inv_obj.search([('folio_id', '=', self.id), ('id', '!=', invoice.id)],
                                                  order='id desc', limit=1)
                    if not last_invoice:
                        invoice.start_electricity_number = self.start_electricity_number
                    else:
                        invoice.start_electricity_number = last_invoice.end_electricity_number
                    references[invoice] = order
                    invoices[group_key] = invoice
                    invoices_origin[group_key] = [invoice.origin]
                    invoices_name[group_key] = [invoice.name]
                elif group_key in invoices:
                    if order.name not in invoices_origin[group_key]:
                        invoices_origin[group_key].append(order.name)
                    if order.client_order_ref and order.client_order_ref not in invoices_name[group_key]:
                        invoices_name[group_key].append(order.client_order_ref)

                if service_line.folio_id:
                    if pending_section:
                        section_invoice = pending_section.invoice_line_create_vals(
                            invoices[group_key].id
                        )
                        inv_line_sequence += 1
                        section_invoice[0]['sequence'] = inv_line_sequence
                        line_vals_list.extend(section_invoice)
                        pending_section = None

                    inv_line_sequence += 1
                    inv_line = service_line.invoice_line_create_vals(
                        invoices[group_key].id
                    )
                    inv_line[0]['sequence'] = inv_line_sequence
                    line_vals_list.extend(inv_line)
            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoices[group_key]] |= order

            self.env['account.invoice.line'].create(line_vals_list)

        for group_key in invoices:
            invoices[group_key].write({'name': ', '.join(invoices_name[group_key]),
                                       'origin': ', '.join(invoices_origin[group_key])})
            sale_orders = references[invoices[group_key]]
            if len(sale_orders) == 1:
                invoices[group_key].reference = sale_orders.reference

        if not invoices:
            raise UserError(_(
                'There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))

        # self._finalize_invoices(invoices, references)
        return [inv.id for inv in invoices.values()]

    def action_open_payment_form(self):
        self.ensure_one()
        room_id = False
        for r in self.room_lines:
            room_id = r.room_id
        return {
            'name': _('Folio Payment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'target': 'new',
            'view_id': self.env.ref('account.view_account_payment_form') and self.env.ref(
                'account.view_account_payment_form').id or False,
            'context': {'default_partner_id': self.partner_id.id, 'default_room_id': room_id.id if room_id else False,
                        'default_folio_id': self.id, 'default_payment_type': 'inbound',
                        'default_room_categ_id': room_id.categ_id.id if room_id and room_id.categ_id else False,
                        'from_follio': True}
        }


class VNAHotelFolioLine(models.Model):
    _inherit = 'hotel.folio.line'

    checkin_date = fields.Datetime('Check In Date', required=True, default=datetime.now())
    checkout_date = fields.Datetime('Check Out Date', required=True, default=datetime.now())
    month_of_rent = fields.Integer(string=_('Month of rent'), default=1)
    room_id = fields.Many2one('hotel.room')
    check_in_status = fields.Selection([
        ('no_check_in', 'Chưa nhận phòng'),
        ('check_in', 'Đã nhận phòng'),
    ], string="Khách nhận phòng", default="no_check_in")
    weekend_price_flag = fields.Boolean(string='Giá cuối tuần')

    @api.multi
    @api.onchange('weekend_price_flag')
    def onchange_room_id(self):
        for r in self:
            if r.weekend_price_flag and r.room_id:
                r.price_unit = r.room_id.weekend_price

    @api.multi
    @api.onchange('room_id')
    def onchange_room_id(self):
        for r in self:
            if r.room_id.room_status == 'no_ready':
                raise UserError(_('Phòng chưa sẵn sàng đón khách!'))
            context = dict(r._context)
            if not context:
                context = {}
            if context.get('folio', False):
                if r.room_id and r.folio_id.partner_id:
                    r.name = 'Tiền thuê ' + (r.room_id.name or '') + ' (' + (r.room_id.categ_id.name or '') + ')'
                    r.product_id = r.room_id.product_id.id
                    r.price_unit = r.room_id.product_id.list_price
                    r.product_uom = r.room_id.product_id.uom_id
                    # tax_obj = self.env['account.tax']
                    # pr = r.room_id.product_id
                    # r.price_unit = tax_obj._fix_tax_included_price(pr.price,
                    #                                                pr.taxes_id,
                    #                                                r.tax_id)
            else:
                if not r.product_id:
                    return {'domain': {'product_uom': []}}
                val = {}
                pr = r.product_id.with_context(
                    lang=r.folio_id.partner_id.lang,
                    partner=r.folio_id.partner_id.id,
                    quantity=val.get('product_uom_qty') or r.product_uom_qty,
                    date=r.folio_id.date_order,
                    pricelist=r.folio_id.pricelist_id.id,
                    uom=r.product_uom.id
                )
                p = pr.with_context(pricelist=r.order_id.pricelist_id.id).price
                if self.folio_id.pricelist_id and r.folio_id.partner_id:
                    obj = self.env['account.tax']
                    val['price_unit'] = obj._fix_tax_included_price(p,
                                                                    pr.taxes_id,
                                                                    r.tax_id)

    @api.multi
    @api.onchange('month_of_rent')
    def onchange_month_of_rent(self):
        for r in self:
            if r.checkin_date and r.month_of_rent:
                r.checkout_date = r.checkin_date + relativedelta(months=r.month_of_rent)

    @api.multi
    @api.onchange('checkin_date', 'checkout_date')
    def on_change_checkout(self):
        for r in self:
            # if r.month_of_rent:
            r.product_uom_qty = 1
            hotel_room_obj = self.env['hotel.room']
            hotel_room_ids = hotel_room_obj.search([])
            avail_prod_ids = []
            avail_room_ids = []
            for room in hotel_room_ids:
                assigned = False
                for rm_line in room.room_line_ids:
                    if rm_line.status != 'cancel' and rm_line.status != 'done':
                        if (r.checkin_date <= rm_line.check_in <=
                            r.checkout_date) or (r.checkin_date <=
                                                 rm_line.check_out <=
                                                 r.checkout_date):
                            assigned = True
                        elif (rm_line.check_in <= r.checkin_date <=
                              rm_line.check_out) or (rm_line.check_in <=
                                                            r.checkout_date <=
                                                            rm_line.check_out):
                            assigned = True
                if room.status != 'occupied':
                    avail_prod_ids.append(room.product_id.id)
                    avail_room_ids.append(room.id)
            domain = {'product_id': [('id', 'in', avail_prod_ids)], 'room_id': [('id', 'in', avail_room_ids)]}
            return {'domain': domain}

    @api.multi
    def _prepare_invoice_line(self):
        for r in self:
            res = {}
            product = r.product_id.with_context(force_company=self.company_id.id)
            account = product.property_account_income_id or product.categ_id.property_account_income_categ_id

            if not account and r.product_id:
                raise UserError(
                    _('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                    (r.product_id.name, r.product_id.id, r.product_id.categ_id.name))
            res = {
                'name': r.name,
                'sequence': r.sequence,
                'origin': r.folio_id.name,
                'account_id': account.id,
                'price_unit': r.price_unit,
                'uom_id': r.product_uom.id,
                'product_id': r.product_id.id or False,
                # 'invoice_line_tax_ids': [(6, 0, r.tax_id.ids)],
                # 'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }
            room_analytic_account = self.env['hotel.room'].search([('product_id', '=', r.product_id.id)])
            if room_analytic_account:
                res.update({'room_id': room_analytic_account.id or False,
                            'account_analytic_id': room_analytic_account.analytic_account_id.id or False,
                            'account_analytic_group': room_analytic_account.analytic_account_id.group_id.id})
                # room_analytic_account.write({'isroom': True})
            return res

    def invoice_line_create_vals(self, invoice_id):
        vals_list = []
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            vals = line._prepare_invoice_line()
            vals.update({'invoice_id': invoice_id})
            vals_list.append(vals)
        return vals_list


class VNAHotelHotelServiceLine(models.Model):
    _inherit = 'hotel.service.line'

    room_id = fields.Many2one('hotel.room')
    room_product_id = fields.Many2one('product.product')

    @api.onchange('room_id')
    def get_product_room(self):
        for r in self:
            if r.room_id:
                room_product = self.env['product.product'].search([('id', '=', r.room_id.product_id.id)])
                r.room_product_id = room_product.id

    @api.onchange('ser_checkin_date', 'ser_checkout_date')
    def on_change_checkout(self):
        res = super(VNAHotelHotelServiceLine, self).on_change_checkout()
        self.product_uom_qty = 1
        return res

    @api.onchange('product_id')
    def product_id_change(self):
        res = super(VNAHotelHotelServiceLine, self).product_id_change()
        if self.folio_id.room_domain_ids:
            self.room_id = self.folio_id.room_domain_ids[0]
        return res

    @api.multi
    def _prepare_invoice_line(self):
        for r in self:
            res = {}
            product = r.product_id.with_context(force_company=self.company_id.id)
            account = product.property_account_income_id or product.categ_id.property_account_income_categ_id

            if not account and r.product_id:
                raise UserError(
                    _('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                    (r.product_id.name, r.product_id.id, r.product_id.categ_id.name))
            res = {
                'name': r.name,
                'sequence': r.sequence,
                'origin': r.folio_id.name,
                'account_id': account.id,
                'price_unit': r.price_unit,
                'uom_id': r.product_uom.id,
                'product_id': r.product_id.id or False,
                # 'invoice_line_tax_ids': [(6, 0, r.tax_id.ids)],
                # 'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            }
            folio = self.env['hotel.folio'].search([('id', '=', r.folio_id.id)], limit=1)
            service_analytic_account = self.env['hotel.service.line'].search(
                [('product_id', '=', r.product_id.id), ('folio_id', '=', folio.id)])
            if service_analytic_account:
                res.update({'room_id': service_analytic_account.room_id.id or False,
                            'account_analytic_id': service_analytic_account.room_id.analytic_account_id.id or False,
                            'account_analytic_group': service_analytic_account.room_id.analytic_account_id.group_id.id,
                            'quantity': r.product_uom_qty})
                r.product_id.write({'isservice': True})
            return res

    def invoice_line_create_vals(self, invoice_id):
        vals_list = []
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            vals = line._prepare_invoice_line()
            vals.update({'invoice_id': invoice_id})
            vals_list.append(vals)
        return vals_list
