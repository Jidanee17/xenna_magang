from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    loan_id = fields.Many2one(
        'equipment.loan',
        string='Peminjaman Terkait',
        readonly=True,
        copy=False,
    )
