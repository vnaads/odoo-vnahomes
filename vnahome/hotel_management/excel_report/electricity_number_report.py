#!/usr/bin/python
# -*- encoding: utf-8 -*-
# Author: locct

from odoo import models, fields, api, _
import base64
from io import BytesIO
from xlsxwriter.workbook import Workbook
from datetime import datetime, date


class vna_electricity_number_report(models.TransientModel):
    _name = 'vna.electricity.number.report'
    _description = "Electricity number report"

    from_date = fields.Date(string="From date", required=True, default=lambda self: date(date.today().year, 1, 1))
    to_date = fields.Date(string="To date", required=True, default=lambda self: date.today())
    data = fields.Binary('File', readonly=True)
    name = fields.Char('Filename', readonly=True)
    hotel_room_type_ids = fields.Many2many('hotel.room.type', 'expense_report_room_type_rel', 'expense_report_id',
                                           'room_type_id', string='Hotel room type')
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.user.company_id)

    def get_company_ids(self):
        company = self.env.user.company_id
        res = [company.id]
        query = "SELECT id FROM res_company WHERE parent_id = %s" % company.id
        self._cr.execute(query)
        for r in self._cr.dictfetchall():
            res.append(r['id'])
        return res

    def get_company_ids_str(self):
        company_ids = self.get_company_ids()
        return ','.join(str(id) for id in company_ids)

    def action_print(self):
        self.ensure_one()
        date_from = self.from_date.strftime('%d-%m-%Y')
        date_to = self.to_date.strftime('%d-%m-%Y')
        report_name = "BC số điện" + date_from + '-' + date_to + '.xlsx'
        parameters = {
            'start_date': self.from_date,
            'end_date': self.to_date,
            'hotel_room_type_ids': '0',
            'company_ids': self.get_company_ids_str()
        }
        if self.hotel_room_type_ids:
            hotel_room_type_ids = ', '.join([str(a.id) for a in self.hotel_room_type_ids])
            parameters.update(hotel_room_type_ids=hotel_room_type_ids)
        parameters.update(query=self.query_str_new(parameters))
        data = self.write_value_report(parameters)
        self.write({'data': data, 'name': report_name})
        return {
            'type': 'ir_actions_vna_download_report',
            'data': {'model': self._name,
                     'options': {},
                     'output_format': report_name,
                     'financial_id': self.id,
                     }
        }

    def write_value_report(self, params):
        query = params['query']
        self._cr.execute(query)
        data = self._cr.dictfetchall()
        buf = BytesIO()
        wb = Workbook(buf)
        ws = wb.add_worksheet('BC SỐ ĐIỆN')
        wb.formats[0].font_name = 'Times New Roman'
        wb.formats[0].font_size = 12
        ws.set_paper(9)
        ws.set_margins(left=0.28, right=0.28, top=0.5, bottom=0.5)
        ws.fit_to_pages(1, 0)  # -- 1 page wide and as long as necessary.
        ws.set_landscape()

        ws.set_column(0, 0, 10)
        ws.set_column(1, 1, 13)
        ws.set_column(2, 2, 10)
        ws.set_column(3, 3, 7)
        ws.set_column(4, 4, 10)
        ws.set_column(5, 5, 35)
        ws.set_column(6, 6, 8)
        ws.set_column(7, 7, 15)
        ws.set_column(8, 8, 15)
        ws.set_column(9, 9, 15)
        ws.set_column(17, 17, 15)
        ws.set_column(18, 18, 15)
        ws.set_row(3, 23)

        #         Style
        title_report_style = wb.add_format({
            'font_color': 'blue',
            'bold': 1,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'font_size': 16,
        })
        table_header = wb.add_format({
            'bold': 1,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Times New Roman',
            'font_size': 11,
        })
        row_default_italic = wb.add_format({
            # 'bold': 1,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'font_name': 'Times New Roman',
            'italic': 1,
        })
        row_default_right = wb.add_format({
            'text_wrap': True,
            'align': 'right',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'font_size': 11,
        })
        row_left_noborder = wb.add_format({
            'text_wrap': True,
            'align': 'left',
            'valign': 'vcenter',
            'border': 0,
            'font_size': 11,
            'font_name': 'Times New Roman',
            'bold': 1,
        })
        row_left_noborder_header = wb.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 0,
            'font_size': 11,
            'font_name': 'Times New Roman',
            'bold': 1,
        })
        row_number = wb.add_format({
            'text_wrap': True,
            'align': 'right',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'border': 1,
            'font_size': 11,
            'num_format': '#,##0.0000',
        })
        row_number_right = wb.add_format({
            'text_wrap': True,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'border': 1,
            'font_size': 11,
            'num_format': '#,##0.0000',
        })
        row_default_bold = wb.add_format({
            'text_wrap': True,
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'border': 1,
            'font_size': 11,
        })
        row_left_bold = wb.add_format({
            'text_wrap': True,
            'bold': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'border': 1,
            'font_size': 11,
            'bg_color': 'gray'
        })
        row_default_left = wb.add_format({
            'text_wrap': True,
            'align': 'left',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'border': 1,
            'font_size': 11,
        })
        row_default_center = wb.add_format({
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'font_size': 11,
        })
        italic = wb.add_format({
            'italic': 1,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
        })
        row_default_right_qty = wb.add_format({
            'text_wrap': True,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Times New Roman',
            'num_format': '#,##0.000',
            'font_size': 11,
        })
        row_default_right_money = wb.add_format({
            'text_wrap': True,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0',
            'font_name': 'Times New Roman',
            'font_size': 11,
        })
        row_bold_right_money = wb.add_format({
            'bold': 1,
            'text_wrap': True,
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0',
            'font_name': 'Times New Roman',
            'font_size': 11,
        })
        row_date_default = wb.add_format({
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            # 'border': 1,
            'font_name': 'Times New Roman',
            'font_size': 11,
            'num_format': 'dd/mm/yyyy',
            'italic': 1,
        })
        row_date_default_left = wb.add_format({
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Times New Roman',
            'font_size': 11,
            'num_format': 'dd/mm/yyyy',
        })
        bold_center = wb.add_format({
            'text_wrap': True,
            'align': 'center',
            'text_wrap': 1,
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
            'bold': 1,
        })
        italic_center = wb.add_format({
            'bold': 1,
            'italic': 1,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_name': 'Times New Roman',
        })
        # HEADER
        user = self.env.user
        company = self.env.user.company_id or False
        # size = (None, 90)
        # img = image_resize_image(company.logo, size, avoid_if_small=True)
        # ws.insert_image('A1', 'logo.png',
        #                 {'image_data': BytesIO(base64.b64decode(img)), 'x_offset': 0, 'y_offset': 0})
        # ------------------------------------ Header -----------------------------------------
        company_name = company and company.name or ''
        addr_from = company.street or ''
        mst = self.env.user.company_id.vat
        row = 1
        ws.write("A{row}".format(row=row), 'Căn', table_header)
        ws.write("B{row}".format(row=row), 'Phòng', table_header)

        end_col = 2
        header_row = 1
        bophan_col = {}
        month_ids = []
        for month in range(self.from_date.month, self.to_date.month + 1):
            month_ids.append(month)

        for month in month_ids:
            ws.write(header_row - 1, end_col, "Tháng " + str(month), table_header)
            ws.set_column(end_col, end_col, 15)
            bophan_col.update({month: end_col})

            end_col += 1

        row += 1
        # Header Table
        for r in data:
            ws.write("A{row}".format(row=row), r['can'] or '', row_default_left)
            ws.write("B{row}".format(row=row), r['phong'] or '', row_default_left)
            for month_row in month_ids:
                month_str = 'thang_' + str(month_row)
                colnum = bophan_col[month_row]
                if r[month_str]:
                    ws.write(row - 1, colnum, abs(r[month_str]), row_default_right_money)
                else:
                    ws.write(row - 1, colnum, '', row_default_right_money)
            row += 1

        wb.close()
        buf.seek(0)
        xlsx_data = buf.getvalue()
        data = base64.encodebytes(xlsx_data)
        return data

    def query_str_new(self, args):
        query = """
        SELECT can, phong,
        sum(thang_1) as thang_1,
        sum(thang_2) as thang_2,
        sum(thang_3) as thang_3,
        sum(thang_4) as thang_4,
        sum(thang_5) as thang_5,
        sum(thang_6) as thang_6,
        sum(thang_7) as thang_7,
        sum(thang_8) as thang_8,
        sum(thang_9) as thang_9,
        sum(thang_10) as thang_10,
        sum(thang_11) as thang_11,
        sum(thang_12) as thang_12
        FROM 
            (SELECT hrt.name as can, pt.name as phong, 
            extract(month from ai.date) as thang,
            case when extract(month from ai.date) = 1 then ail.quantity else 0 end as thang_1,
            case when extract(month from ai.date) = 2 then ail.quantity else 0 end as thang_2,
            case when extract(month from ai.date) = 3 then ail.quantity else 0 end as thang_3,
            case when extract(month from ai.date) = 4 then ail.quantity else 0 end as thang_4,
            case when extract(month from ai.date) = 5 then ail.quantity else 0 end as thang_5,
            case when extract(month from ai.date) = 6 then ail.quantity else 0 end as thang_6,
            case when extract(month from ai.date) = 7 then ail.quantity else 0 end as thang_7,
            case when extract(month from ai.date) = 8 then ail.quantity else 0 end as thang_8,
            case when extract(month from ai.date) = 9 then ail.quantity else 0 end as thang_9,
            case when extract(month from ai.date) = 10 then ail.quantity else 0 end as thang_10,
            case when extract(month from ai.date) = 11 then ail.quantity else 0 end as thang_11,
            case when extract(month from ai.date) = 12 then ail.quantity else 0 end as thang_12
            FROM account_invoice ai
            LEFT JOIN account_invoice_line ail ON ail.invoice_id = ai.id
            LEFT JOIN (select product.id, product.product_tmpl_id, invoice_line.invoice_id 
                      from account_invoice_line invoice_line 
                      left join product_product product ON invoice_line.product_id = product.id 
                      where product.isroom = 't') 
                      pp ON pp.invoice_id = ail.invoice_id
            LEFT JOIN hotel_room hr ON hr.product_id = pp.id
            LEFT JOIN hotel_room_type hrt ON hrt.id = hr.categ_id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN product_product invoice_product ON invoice_product.id = ail.product_id
            WHERE (ai.date >= cast('{start_date}' as date) AND ai.date <= cast('{end_date}' as date)) 
            AND invoice_product.is_electric_type = 't'
            and case when '{hotel_room_type_ids}' != '0' then hrt.id in ({hotel_room_type_ids}) else 1=1 end
            and ai.company_id in ({company_ids})
            ORDER BY hrt.name, pt.name) as result
        GROUP BY can, phong
        ORDER BY can, phong
        """
        query = query.format(**args)
        return query
