from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_damaged = fields.Boolean(
        string='Rusak',
        help=(
            'Ditandai jika alat dalam kondisi rusak dan '
            'tidak boleh dipinjamkan.'
        )
    )

    penalty_amount = fields.Monetary(
        string='Nominal Denda Kehilangan',
        currency_field='currency_id',
        help=(
            'Nominal denda yang dikenakan jika alat ini dinyatakan '
            'hilang saat dipinjam. Jika dikosongkan, sistem akan '
            'memakai Sales Price (list_price) sebagai basis denda.'
        )
    )
