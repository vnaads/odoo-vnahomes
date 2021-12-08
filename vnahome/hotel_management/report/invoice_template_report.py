# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import locale
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

if os.name == 'nt':  # if are Windows OS
    locale.setlocale(locale.LC_ALL, '')
else:
    locale.setlocale(locale.LC_ALL, 'vi_VN.utf8')


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def _get_report_vna_filename(self):
        self.ensure_one()
        file_name = ''
        if self.date_invoice:
            file_name = (self.room_id.categ_id.name or '') + '/' + (self.room_id.name or '') + '/' + 'Tháng - ' + (
                        self.date_invoice + relativedelta(months=1)).strftime('%m')
        else:
            file_name = (self.room_id.categ_id.name or '') + '/' + (self.room_id.name or '') + '/' + 'Tháng - ' + (
                    datetime.now().date() + relativedelta(months=1)).strftime('%m')
        return file_name

    @api.multi
    def _get_data(self):
        self.ensure_one()
        lines = []
        note_line = []
        i = 1
        # there are only 3 taxes: 0%, 5% and 10%
        TAX_TYPES = [0, 5, 10]
        taxes = {str(i): {'total_unit_price': 0,
                          'vat': 0,
                          'total_price': 0} for i in TAX_TYPES}
        total_unit_price = vat = total_price = 0

        sql_data = """
                select
                --pp.name_template,
                ail.name as name_template, pp.id as product_id,
                    --uu.name uom,
                    sum(ail.quantity) quantity,
                    --COALESCE(ail.discount,0) as discount, 
                    COALESCE(ail.price_unit, 0) as price_unit,
                    sum(ail.quantity*COALESCE(ail.price_unit,0)) total_unit_price,
                    sum(ail.price_subtotal) as price_subtotal,
                    --sum(ail.x_rounding_subtotal) as rounding_total_unit_price,
                    --sum(ail.x_rounding_price_tax) as rounding_price_tax,
                    (select sum(amount) from account_invoice_line_tax rel
                    left join account_tax at on at.id = rel.tax_id
                    left join account_invoice_line ai on ai.id = rel.invoice_line_id
                    where rel.invoice_line_id = ail.id) as tax
                          from account_invoice_line ail
                        left join account_invoice ai on ai.id = ail.invoice_id
                        left join product_product pp on pp.id = ail.product_id
                        left join uom_uom uu on uu.id = ail.uom_id
                        where invoice_id = %d
                        group by
                        --name_template,
                        ail.name, pp.id,
                        price_unit, tax,ail.discount
                        ORDER BY tax,total_unit_price ASC
                """ \
                   % (self.id)
        self.env.cr.execute(sql_data)
        da = self.env.cr.dictfetchall()

        line_last_tax_0 = line_last_tax_5 = line_last_tax_10 = None
        for invoice_line in da:
            total_tax = invoice_line['tax'] or 0.0
            # invoice_line['total_unit_price'] = round(invoice_line['total_unit_price'], 0)
            product_obj = []
            if invoice_line['product_id']:
                product_obj = self.env['product.product'].search([('id', '=', int(invoice_line['product_id']))])
                item = {
                    'order': i,
                    'product': product_obj[0].name if product_obj else '',
                    'description': invoice_line['name_template'] or '',
                    # 'uom': invoice_line['uom'],
                    'quantity': invoice_line['quantity'] or 0,
                    'price_unit': round(invoice_line['price_unit']) or 0,
                    'price_subtotal': round(invoice_line['price_subtotal']) or 0,
                    # 'discount': invoice_line['discount'],
                    # 'total_unit_price': invoice_line['rounding_total_unit_price'] or 0,
                    # 'tax': int(total_tax * 100),
                    'tax': int(total_tax),
                    # 'vat':  round(invoice_line['rounding_price_tax']) if invoice_line['rounding_price_tax'] and invoice_line['rounding_price_tax'] != 0
                    #                 else round(invoice_line['total_unit_price'] * total_tax),
                    # 'not_round_vat': round(invoice_line['rounding_price_tax']) if invoice_line['rounding_price_tax'] and invoice_line['rounding_price_tax'] != 0
                    #                 else invoice_line['total_unit_price'] * total_tax,
                    # 'rounding_price_tax': round(invoice_line['rounding_price_tax']) if invoice_line['rounding_price_tax'] else 0,
                    # 'total_price': (invoice_line['rounding_total_unit_price'] or 0) +(round(invoice_line['rounding_price_tax']) if invoice_line['rounding_price_tax'] and invoice_line['rounding_price_tax'] != 0
                    #                 else round(invoice_line['total_unit_price'] * total_tax)),

                }
                i += 1
                lines.append(item)
            else:
                item = {
                    'note': invoice_line['name_template'] or '',
                }
                note_line.append(item)
            # if str(int(total_tax * 100)) in taxes and (total_tax * 100) in [0.0, 5.0, 10.0]:
            #     key = str(int(total_tax * 100))
            # if str(int(total_tax)) in taxes and (total_tax) in [0.0, 5.0, 10.0]:
            #     key = str(int(total_tax))
            #     taxes[key]['total_unit_price'] += item['total_unit_price']
            #     taxes[key]['vat'] += item['not_round_vat']
            #     taxes[key]['total_price'] += item['total_price']
            #     # lay gia tri line cuoi
            #     # if total_tax * 100 == 0.0 and item['price_unit'] != 0.0:
            #     #     line_last_tax_0 = item
            #     # if total_tax * 100 == 5.0 and item['price_unit'] != 0.0:
            #     #     line_last_tax_5 = item
            #     # if total_tax == 10.0 and item['price_unit'] != 0.0:
            #     #     line_last_tax_10 = item
            #     if total_tax == 0.0 and item['price_unit'] != 0.0:
            #         line_last_tax_0 = item
            #     if total_tax == 5.0 and item['price_unit'] != 0.0:
            #         line_last_tax_5 = item
            #     if total_tax == 10.0 and item['price_unit'] != 0.0:
            #         line_last_tax_10 = item
            # vat += item['not_round_vat']
            # total_unit_price += item['total_unit_price']
            # total_price += item['total_price']

        vals = {
            # 'total_price_to_word': self.env['res.currency']._num2word(round(total_price)),
            # 'total_unit_price': total_unit_price,
            # 'total_price': total_price,
            'vat': vat,
        }
        # sql = """
        #         SELECT so.name FROM account_invoice ai
        #         INNER JOIN stock_picking sp ON ai.origin = sp.name
        #         INNER JOIN stock_picking_type spt ON sp.picking_type_id = spt.id AND spt.code = 'outgoing'
        #         INNER JOIN sale_order so ON so.name = sp.origin
        #         WHERE ai.id = %s
        #         """ % self.id
        # self._cr.execute(sql)
        # res = self._cr.fetchone()
        # # get vat partner
        # vat_partner = self.x_vat_partner
        # if self.partner_id:
        #     contacts = self.partner_id.child_ids.filtered(lambda x: x.type == 'invoice' )
        #     if len(contacts) > 0:
        #         vat_partner = contacts[0].name
        # lines_origin = lines[:]
        # supp_invoice = self.supplier_invoice_number or '..........'
        # date = (datetime.strftime(self.registration_date, '%d-%m-%Y')) or '...........'
        # if len(lines) > 10:
        #     lines_gro = []
        #     vat = total_unit_price = total_price = 0
        #     for r in lines:
        #         vat += r['vat']
        #         total_unit_price += r['total_unit_price']
        #         total_price += r['total_price']
        #     lines_gro.append({
        #         'order' : 1,
        #         'product' : u"Xuất bản " + u" kèm theo bảng kê số " + supp_invoice
        #                         + u' ngày ' + date,
        #         # 'product': u"Xuất bản "  + u"  kèm theo bảng kê số " + supp_invoice
        #         #            + u' ngày ' + (date),
        #         'lot' : None,
        #         'expired_date' : None,
        #         'uom' : None,
        #         'quantity' : None,
        #         'price_unit' : None,
        #         'discount' : None,
        #         'tax': None,
        #         'total_unit_price' : total_unit_price,
        #         'total_price' : total_price,
        #         'vat' : vat,
        #     })
        #     lines = lines_gro

        data = {
            # 'vat_partner': vat_partner,
            'lines': lines,
            # 'lines_origin': lines_origin,
            'vals': vals,
            'taxes': taxes,
            'locale': locale,
            'note_line': note_line
            # 'sale_order': self.x_origin or (res and res[0] or ''),
            # 'sale_order': self.origin or (res and res[0] or ''),
            # 'sale_order_origin': self.x_sale_order_origin or ''
        }
        return data


class AccountReportInvoice(models.AbstractModel):
    _name = 'report.account.report_invoice'
    _description = "report.account.report_invoice"

    @api.model
    def _get_report_values(self, docids, data=None):
        invoice = self.env['account.invoice'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.invoice',
            'docs': invoice,
            'data': data,
        }


class AccountReportInvoiceEng(models.AbstractModel):
    _name = 'report.hotel_management.report_invoice_eng'
    _description = "report.hotel_management.report_invoice_eng"

    @api.model
    def _get_report_values(self, docids, data=None):
        invoice = self.env['account.invoice'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.invoice',
            'docs': invoice,
            'data': data,
        }
