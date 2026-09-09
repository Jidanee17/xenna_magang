from odoo import models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    equipment_loan_line_ids = fields.One2many(
        'equipment.loan.line',
        'lot_id',
        string='Equipment Loan Lines',
    )
