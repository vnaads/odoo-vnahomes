from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_electric_type = fields.Boolean(string='Is electricity type', default=False)
