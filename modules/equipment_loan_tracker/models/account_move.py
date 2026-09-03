from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    loan_id = fields.Many2one(
        'equipment.loan',
        string='Peminjaman Terkait',
        readonly=True,
        copy=False,
    )
