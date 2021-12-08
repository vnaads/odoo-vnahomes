# coding: utf-8
import base64
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition


class FileDispatcher(http.Controller):

    @http.route('/vna_download_report', type='http', auth='user', methods=['POST'], csrf=False)
    def z_download_report(self, model, options, output_format, token, financial_id=None, **kw):
        if output_format and '.doc' in output_format:
            return self.export_docx(model, 'data', financial_id, output_format, **kw)
        return self.export_xlsx(model, 'data', financial_id, output_format, **kw)

    @http.route('/report_xlsx/download', type='http', auth='user')
    def export_xlsx(self, model, field, report_id, file_name="report.xlsx", **kw):
        model = request.env[model]
        res = model.search_read([('id', '=', int(report_id))])
        if res:
            res = res[0]
        else:
            return request.not_found()

        file_content = base64.b64decode(res[field] or '')
        if not file_content:
            return request.not_found()
        else:
            if not file_name:
                file_name = '%s_%s' % (model.replace('.', '_'), id)
        return request.make_response(file_content, [
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', content_disposition(file_name))])
