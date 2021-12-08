# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    account_analytic_group = fields.Many2one('account.analytic.group', string='Analytic Account Group', groups="analytic.group_analytic_accounting")

    _depends = {
        'account.invoice': [
            'account_id', 'amount_total_company_signed', 'commercial_partner_id', 'company_id',
            'currency_id', 'date_due', 'date_invoice',
            'journal_id', 'number', 'partner_bank_id', 'partner_id', 'payment_term_id',
            'residual', 'state', 'type', 'user_id',
        ],
        'account.invoice.line': [
            'account_id', 'invoice_id', 'price_subtotal', 'product_id',
            'quantity', 'uom_id', 'account_analytic_id', 'account_analytic_group'
        ],
        'product.product': ['product_tmpl_id'],
        'product.template': ['categ_id'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        # 'res.partner': ['country_id'],
    }

    def _select(self):
        select_str = """
            SELECT sub.id, sub.number, sub.date, sub.product_id, sub.partner_id, sub.account_analytic_id, sub.account_analytic_group,
                sub.payment_term_id, sub.uom_name, sub.currency_id, sub.journal_id,
                sub.user_id, sub.company_id, sub.nbr, sub.invoice_id, sub.type, sub.state,
                sub.date_due, sub.account_id, sub.account_line_id, sub.partner_bank_id,
                sub.product_qty, sub.price_total as price_total, sub.price_average as price_average, sub.amount_total / COALESCE(cr.rate, 1) as amount_total,
                COALESCE(cr.rate, 1) as currency_rate, sub.residual as residual, sub.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _sub_select(self):
        select_str = """
                SELECT ail.id AS id,
                    ai.date_invoice AS date,
                    ai.number as number,
                    ail.product_id, ai.partner_id, ai.payment_term_id, ail.account_analytic_id, ail.account_analytic_group,
                    u2.name AS uom_name,
                    ai.currency_id, ai.journal_id, ai.user_id, ai.company_id,
                    1 AS nbr,
                    ai.id AS invoice_id, ai.type, ai.state, ai.date_due, ai.account_id, ail.account_id AS account_line_id,
                    ai.partner_bank_id,
                    SUM ((invoice_type.sign_qty * ail.quantity) / COALESCE(u.factor,1) * COALESCE(u2.factor,1)) AS product_qty,
                    SUM(ail.price_subtotal_signed * invoice_type.sign) AS price_total,
                    SUM(ail.price_total * invoice_type.sign_qty) AS amount_total,
                    SUM(ABS(ail.price_subtotal_signed)) / CASE
                            WHEN SUM(ail.quantity / COALESCE(u.factor,1) * COALESCE(u2.factor,1)) <> 0::numeric
                               THEN SUM(ail.quantity / COALESCE(u.factor,1) * COALESCE(u2.factor,1))
                               ELSE 1::numeric
                            END AS price_average,
                    ai.residual_company_signed / (SELECT count(*) FROM account_invoice_line l where invoice_id = ai.id) *
                    count(*) * invoice_type.sign AS residual,
                    ai.commercial_partner_id as commercial_partner_id
        """
        return select_str

    def _from(self):
        from_str = """
                FROM account_invoice_line ail
                JOIN account_invoice ai ON ai.id = ail.invoice_id
                JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                JOIN res_partner partner_ai ON ai.partner_id = partner_ai.id
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                left JOIN product_template pt ON pt.id = pr.product_tmpl_id
                LEFT JOIN uom_uom u ON u.id = ail.uom_id
                LEFT JOIN uom_uom u2 ON u2.id = pt.uom_id
                JOIN (
                    -- Temporary table to decide if the qty should be added or retrieved (Invoice vs Credit Note)
                    SELECT id,(CASE
                         WHEN ai.type::text = ANY (ARRAY['in_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN -1
                            ELSE 1
                        END) AS sign,(CASE
                         WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                            THEN -1
                            ELSE 1
                        END) AS sign_qty
                    FROM account_invoice ai
                ) AS invoice_type ON invoice_type.id = ai.id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
                GROUP BY ail.id, ail.product_id, ail.account_analytic_id, ail.account_analytic_group, ai.date_invoice, ai.id,
                    ai.partner_id, ai.payment_term_id, u2.name, u2.id, ai.currency_id, ai.journal_id,
                     ai.user_id, ai.company_id, ai.id, ai.type, invoice_type.sign, ai.state, 
                    ai.date_due, ai.account_id, ail.account_id, ai.partner_bank_id, ai.residual_company_signed,
                    ai.amount_total_company_signed, ai.commercial_partner_id
        """
        return group_by_str
