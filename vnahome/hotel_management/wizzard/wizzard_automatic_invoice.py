# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class WizardAutomaticInvoice(models.TransientModel):
    _name = "wizard.automatic.invoice"
    _description = "Invoice Automation"

    invoice_date = fields.Date(string="Invoice date", default=lambda self: date.today(), required=True)
    folio_id = fields.Many2one('hotel.folio', string="Hotel folio")

    @api.multi
    def invoice_create_calculation(self):
        for r in self:
            if not r.folio_id:
                folio_obj = self.env['hotel.folio'].search([('state', '=', 'sale')])
                for folio in folio_obj:
                    if folio.room_lines[0].filtered(lambda x: x.checkin_date <= r.invoice_date and x.checkout_date >= r.invoice_date):
                        invoice_of_folio = self.env['account.invoice'].search([('folio_id', '=', folio.id)]).filtered(
                            lambda x: x.date and x.date.month == r.invoice_date.month and x.date.year == r.invoice_date.year)
                        if invoice_of_folio:
                            raise ValidationError(
                                _('Hợp đồng số %s - Khách hàng %s - %s (%s) - Từ %s đến %s không thỏa mãn điều kiện tạo hóa đơn!') % (
                                    folio.name, folio.partner_id.name, folio.room_id.name, folio.room_id.categ_id.name,
                                    folio.room_lines[0].checkin_date.strftime('%d/%m/%Y'), folio.room_lines[0].checkout_date.strftime('%d/%m/%Y')))
                        else:
                            invoice = folio.action_create_invoice(grouped=False, final=False)
                            invoice.write({'date_invoice': r.invoice_date, 'date': r.invoice_date})
                    else:
                        raise ValidationError(_('Hợp đồng số %s - Khách hàng %s - %s (%s) - Từ %s đến %s không thỏa mãn điều kiện tạo hóa đơn!') % (
                            folio.name, folio.partner_id.name, folio.room_id.name, folio.room_id.categ_id.name,
                            folio.room_lines[0].checkin_date.strftime('%d/%m/%Y'),
                            folio.room_lines[0].checkout_date.strftime('%d/%m/%Y')))
            else:
                if r.folio_id.room_lines[0].filtered(lambda x: x.checkin_date <= r.invoice_date and x.checkout_date >= r.invoice_date):
                    invoice_of_folio = self.env['account.invoice'].search([('folio_id', '=', r.folio_id.id)]).filtered(
                        lambda x: x.date and x.date.month == r.invoice_date.month and x.date.year == r.invoice_date.year)
                    if invoice_of_folio:
                        raise ValidationError(_('Hợp đồng số %s - Khách hàng %s - %s (%s) - Từ %s đến %s không thỏa mãn điều kiện tạo hóa đơn!') % (
                            r.folio_id.name, r.folio_id.partner_id.name, r.folio_id.room_id.name, r.folio_id.room_id.categ_id.name,
                            r.folio_id.room_lines[0].checkin_date.strftime('%d/%m/%Y'), r.folio_id.room_lines[0].checkout_date.strftime('%d/%m/%Y')))
                    else:
                        invoice = r.folio_id.action_create_invoice(grouped=False, final=False)
                        self.env['account.invoice'].browse(invoice).write({'date_invoice': r.invoice_date, 'date': r.invoice_date})
                else:
                    raise ValidationError(_('Hợp đồng số %s - Khách hàng %s - %s (%s) - Từ %s đến %s không thỏa mãn điều kiện tạo hóa đơn!') % (
                        r.folio_id.name, r.folio_id.partner_id.name, r.folio_id.room_id.name, r.folio_id.room_id.categ_id.name,
                        r.folio_id.room_lines[0].checkin_date.strftime('%d/%m/%Y'),
                        r.folio_id.room_lines[0].checkout_date.strftime('%d/%m/%Y')))
