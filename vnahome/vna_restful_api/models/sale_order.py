# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, tools, http, exceptions
from datetime import datetime, date, time, timedelta
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import json
from odoo.http import request, Response
from odoo.tools import SUPERUSER_ID

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # gmo_code = fields.Char(string='GMO code', copy=False)
    #
    # _sql_constraints = [('unique_gmo_code', 'UNIQUE(gmo_code)', "gmo_code must be unique")]

    @api.multi
    def create_sale_order_for_dap(self, values):
        if not values:
            return {
                "result": "Error",
                "message": _("Error 01: sale order data is required but not found!")
            }
        so_vals = dict()
        message = ''

        partner_ref = values.get('CUSTOMER_ID', False)
        if not partner_ref:
            message += _('\nError 01: CUSTOMER_ID is required but not found')
        else:
            try:
                partner_ref = str(partner_ref).strip()
                partner = self.env['res.partner'].search([
                    ('ref', '=', partner_ref),
                    ('customer', '=', True)], limit=1)
                if not partner:
                    message += _('\nError 02: Cannot find customer with code {}').format(partner_ref)
                else:
                    so_vals['partner_id'] = partner.id
            except ValueError:
                message += _('\nError 03: Wrong value for CUSTOMER_ID')

        check_baogia = values.get('IS_LOGISTICS', False)  # true: logistic order, false: commercial order
        if check_baogia:
            so_vals['check_baogia'] = True
            x_check_logistics_order = values.get('IS_ORDER', False)
            if x_check_logistics_order:
                so_vals['x_check_logistics_order'] = True
                x_owner_ref = values.get('OWNER_ID', False)  # x_owner_id: logistics owner
                if not x_owner_ref:
                    message += _('\nError 01: OWNER_ID is required but not found')
                else:
                    try:
                        x_owner_ref = str(x_owner_ref).strip()
                        x_owner = self.env['res.partner'].search([
                            ('ref', '=', x_owner_ref),
                            ('is_owner', '=', True)
                        ], limit=1)
                        if not x_owner:
                            message += _('\nError 02: Can not find Owner with OWNER_ID {}').format(x_owner_ref)
                        else:
                            so_vals['x_owner_id'] = x_owner.id
                    except ValueError:
                        message += _('\nError 03: Wrong value for OWNER_ID')

                x_total_amount_orders = values.get('TOTAL_AMOUNT', 0.0)
                if not x_total_amount_orders:
                    message += _('\nError 01: TOTAL_AMOUNT is required but not found')
                else:
                    try:
                        x_total_amount_orders = float(x_total_amount_orders)
                        if x_total_amount_orders <= 0:
                            message += _('\nError 04: TOTAL_AMOUNT must be greater than 0!')
                        else:
                            so_vals['x_total_amount_orders'] = x_total_amount_orders
                            so_vals['x_total_value_of_orders'] = x_total_amount_orders
                    except ValueError:
                        message += _('\nError 03: Wrong value for TOTAL_AMOUNT')

                x_number_partner = values.get('INVOICE_NUMBER', False)
                if x_number_partner:
                    try:
                        x_number_partner = str(x_number_partner).strip()
                        so_vals['x_number_partner'] = x_number_partner
                    except ValueError:
                        message += _('\nError 03: Wrong value for INVOICE_NUMBER')

                x_picking_partner = values.get('PICKING', False)
                if x_picking_partner:
                    try:
                        x_picking_partner = str(x_picking_partner).strip()
                        so_vals['x_picking_partner'] = x_picking_partner
                    except ValueError:
                        message += _('\nError 03: Wrong value for PICKING')
            else:
                so_vals['x_check_logistics_order'] = False
                x_logistics_service = values.get('QUOTATION_TYPE', False)
                if not x_logistics_service:
                    message += _('\nError 01: QUOTATION_TYPE is required but not found')
                else:
                    try:
                        x_logistics_service = int(x_logistics_service)
                        if x_logistics_service in (1, 2, 3, 4):
                            so_vals['x_logistics_service'] = x_logistics_service
                        else:
                            message += _('\nError 04: QUOTATION_TYPE must be one of following number: 1, 2, 3, 4')
                    except ValueError:
                        message += _('\nError 03: Wrong value for QUOTATION_TYPE')

        else:
            so_vals['x_check_logistics_order'] = False
            partner_debt_ref = values.get('PARTNER_DEBT_ID', False)  # partner_debt_id: commercial owner
            if not partner_debt_ref:
                message += _('\nError 01: PARTNER_DEBT_ID is required but not found')
            else:
                try:
                    partner_debt_ref = str(partner_debt_ref).strip()
                    partner_debt = self.env['res.partner'].search([
                        ('ref', '=', partner_debt_ref),
                    ], limit=1)
                    if not partner_debt:
                        message += _('\nError 02: Cannot find partner debt with code {}').format(partner_debt_ref)
                    else:
                        # find all partner debt of the current customer
                        partner_debt_list = self.env['z.partner.debt'].search([
                            ('partner_id', '=', partner and partner.id)
                        ]).mapped('customer_id')
                        # check if the partner debt is in the list of partner debt
                        if partner_debt_list and partner_debt in partner_debt_list:
                                so_vals['partner_debt_id'] = partner_debt.id
                        else:
                            message += _('\nError 04: Customer {} does not have PARTNER_DEBT_ID {}').format(partner_ref, partner_debt_ref)
                except ValueError:
                    message += _('\nError 03: Wrong value for OWNER_ID')

        sale_person_id = values.get('SALESMAN_ID', False)
        if sale_person_id:
            try:
                sale_person_id = str(sale_person_id).strip()
                sale_person = self.env['res.partner'].search([
                    ('ref', '=', sale_person_id),
                    ('x_is_saleperson', '=', True)
                ], limit=1)
                if not sale_person:
                    message += _('\nError 02: Can not find salesperson with ref {}').format(sale_person_id)
                else:
                    so_vals['sale_person_id'] = sale_person.id
            except ValueError:
                message += _('\nError 03: Wrong value for SALEPERSON_ID')
        elif not sale_person_id and not check_baogia:
            message += _('\n SALESMAN_ID is required for commercial sale order but not found')

        partner_invoice_ref = values.get('INVOICE_ADDRESS', False)
        if not partner_invoice_ref:
            so_vals['partner_invoice_id'] = partner and so_vals['partner_id']
        else:
            try:
                partner_invoice_ref = str(partner_invoice_ref).strip()
                partner_invoice = self.env['res.partner'].search([
                    ('ref', '=', partner_invoice_ref),
                    ('type', '=', 'invoice')
                ], limit=1)
                if not partner_invoice:
                    message += _('\nError 02: Cannot find invoice address with reference code {}').format(partner_invoice_ref)
                else:
                    if partner_invoice.parent_id != so_vals['partner_id']:
                        message += _('\nError 04: Invoice address with ref code {} does not belong to this customer').format(partner_invoice_ref)
                    else:
                        so_vals['partner_invoice_id'] = partner_invoice.id
            except ValueError:
                message += _('\nError 03: Wrong value for INVOICE_ID')

        partner_shipping_ref = values.get('SHIPPING_ADDRESS', False)
        if not partner_shipping_ref:
            so_vals['partner_shipping_id'] = partner and so_vals['partner_id']
        else:
            try:
                partner_shipping_ref = str(partner_shipping_ref).strip()
                partner_shipping = self.env['res.partner'].search([
                    ('ref', '=', partner_shipping_ref),
                    ('type', '=', 'delivery')
                ], limit=1)
                if not partner_shipping:
                    message += _('\nError 02: Cannot find shipping address with reference code {}').format(partner_shipping_ref)
                else:
                    if partner_shipping.parent_id != so_vals['partner_id']:
                        message += _('\nError 04: Shipping address with ref code {} does not belong to this customer').format(
                            partner_invoice_ref)
                    else:
                        so_vals['partner_invoice_id'] = partner_shipping.id
            except ValueError:
                message += _('\nError 03: Wrong value for INVOICE_ID')

        warehouse_id = values.get('WAREHOUSE_ID', False)
        if not warehouse_id:
            message += _('\nError 01: WAREHOUSE_ID is required but not found')
        else:
            try:
                warehouse_id = str(warehouse_id).strip()
                warehouse = self.env['stock.warehouse'].search([('code', '=', warehouse_id)], limit=1)
                if not warehouse:
                    message += _('\nError 02: Can not find warehouse with code {}').format(warehouse_id)
                else:
                    so_vals['warehouse_id'] = warehouse.id
            except ValueError:
                message += _('\nError 03: Wrong value for WAREHOUSE_ID')

        payment_term_id = values.get('PAYMENT_TERM', False)
        if not payment_term_id:
            message += _('\nError 01: PAYMENT_TERM is required but not found')
        else:
            try:
                payment_term_id = str(payment_term_id).strip()
                payment_term = self.env['account.payment.term'].search([('name', '=', payment_term_id)], limit=1)
                if not payment_term:
                    message += _('\nError 02: Can not find payment term with value {}').format(payment_term_id)
                else:
                    so_vals['payment_term_id'] = payment_term.id
            except ValueError:
                message += _('\nError 03: Wrong value for payment term')

        company_id = values.get('COMPANY_ID', False)
        if company_id:
            try:
                company_id = str(company_id).strip()
                company = self.env['res.company'].search([
                    ('name', '=', company_id)
                ], limit=1)
                if not company:
                    message += _('\nError 02: Can not find company with name {}').format(company_id)
                else:
                    so_vals['company_id'] = company.id
            except ValueError:
                message += _('\nError 03: Wrong value for COMPANY_ID')

        list_promotion = values.get('PROMOTION_CODE', [])
        if list_promotion:
            promotion_list = []
            try:
                for promo_code in list_promotion:
                    promo = self.env['sale.coupon.program'].search([
                        ('name', '=', promo_code)
                    ], limit=1)
                    if not promo:
                        message += _('\nError 02: Can not find promotion program with code {}').format(promo_code)
                    else:
                        promotion_list.append(promo.name)
                so_vals['note'] = str(promotion_list).replace('[', '').replace(']', '')
            except ValueError:
                message += _('\nError 03: Wrong value for PROMOTION_CODE')

        so_vals['state'] = 'draft'

        """ calculate sale order line fields' value
        """
        line_list = list()
        so_lines = values.get('so_line', [])
        if not so_lines:
            message += _('\nError 01: Sale order detail is required but not found!')
        else:
            for line in so_lines:
                line_vals = dict()
                product_code = line.get('PRODUCT_CODE', False)
                if not product_code:
                    message += _('\nError 01: SO detail: product is required but not found!')
                else:
                    try:
                        product_code = str(product_code).strip()
                        product = self.env['product.product'].search([
                            ('default_code', '=', product_code)
                        ], limit=1)
                        if not product:
                            message += _('\nError 02: Can not find product with code {}!').format(product_code)
                        else:
                            line_vals['product_id'] = product.id
                            line_vals['name'] = product.name
                    except ValueError:
                        message += _('\nError 03: Wrong value for PRODUCT_CODE {}').format(product_code)
                # get product uom
                uom_code = line.get('PRODUCT_UOM', False)
                if not uom_code:
                    message += _('\nError 01: Unit of measure is required but not found')
                else:
                    try:
                        uom_code = str(uom_code).strip()
                        uom = self.env['uom.uom'].search([('name', '=', uom_code)], limit=1)
                        if not uom:
                            message += _('\nError  02: Can not find Unit of measure {}!').format(uom_code)
                        else:
                            line_vals['product_uom'] = uom.id
                    except ValueError:
                        message += _("\nError 03: Wrong value for product's UOM")

                # get product quantity
                qty = line.get('QTY', 0)
                try:
                    qty = float(qty)
                    if qty <= 0:
                        message += _('\nError 04: QTY {} must be greater than 0!').format(product_code)
                    else:
                        line_vals['product_uom_qty'] = qty
                except ValueError as e:
                    message += _('\nError 03: Quantity of product {} must be a number!').format(product_code)

                # get price unit
                price_unit = line.get('PRICE', 0)
                try:
                    price_unit = float(price_unit)
                    if price_unit <= 0:
                        message += _('\nError 04: Price of product {} must be greater than 0!').format(product_code)
                    else:
                        line_vals['price_unit'] = price_unit
                except ValueError as e:
                    message += _('\nError 02: Price of product {} must be a number!').format(product_code)

                discount = line.get('DISCOUNT', 0.0)
                if discount:
                    try:
                        discount = float(discount)
                        if discount < 0:
                            message += _('\nError 04: Discount must not be negative')
                        else:
                            line_vals['discount'] = discount
                    except ValueError:
                        message += _('\nError 03: Wrong value for DISCOUNT')

                sale_amount_discount = line.get('AMOUNT_DISCOUNT', 0.0)
                if sale_amount_discount:
                    try:
                        sale_amount_discount = float(sale_amount_discount)
                        if sale_amount_discount < 0:
                            message += _('\nError 04: AMOUNT_DISCOUNT must not be negative')
                        else:
                            line_vals['sale_amount_discount'] = sale_amount_discount
                    except ValueError:
                        message += _('\nError 03: Wrong value for AMOUNT_DISCOUNT')

                line_list.append((0, 0, line_vals))

        so_vals['order_line'] = line_list

        if message != '':
            return {
                'RESULT': _('ERROR'),
                'MESSAGE': message
                }
        else:
            so = self.env['sale.order'].create(so_vals)
            # so.action_confirm()
            return {
                'RESULT': _('SUCCESS'),
                'MESSAGE': _('Sale order is created'),
                'SO_ID': so.id,
                'SO_NAME': so.name
            }

    @api.multi
    def get_sale_order_state_for_dap(self, values):
        message = ''
        result = {}
        if not values:
            message += _('\nError 01: ORDER_IDS is required but not found')
        else:
            for so_id in values:
                try:
                    order = self.env['sale.order'].browse(so_id)
                    if order:
                        result.update({so_id: order['state']})
                except exceptions.MissingError:
                    result.update({so_id: 'Error 02: ID not found'})
                except:
                    result.update({so_id: 'Error 03: Wrong ID value'})
        if message != '':
            return {
                'RESULT': _('ERROR'),
                'MESSAGE': message
            }
        else:
            return {
                'RESULT': _('SUCCESS'),
                'MESSAGE': result
            }
