from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    loan_id = fields.Many2one(
        'equipment.loan',
        string='Peminjaman Terkait',
        readonly=True,
        copy=False,
    )


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    loan_line_id = fields.Many2one(
        'equipment.loan.line',
        string='Equipment Loan Line',
        readonly=True,
        copy=False,
        ondelete='set null',
    )
