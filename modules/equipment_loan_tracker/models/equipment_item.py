import re

from odoo import models, fields, api


class EquipmentItem(models.Model):
    _name = 'equipment.item'
    _description = 'Equipment Item'

    _sql_constraints = [
        (
            'equipment_code_unique',
            'UNIQUE(code)',
            'Kode inventaris alat harus unik.'
        ),
    ]

    _CATEGORY_PREFIX = {
        'elektronik': 'ELEC',
        'kantor': 'OFF',
        'lainnya': 'OTH',
    }

    name = fields.Char(
        string='Nama Alat',
        required=True
    )

    code = fields.Char(
        string='Kode Inventaris',
        required=True,
        readonly=True,
        copy=False,
        default='New'
    )

    category = fields.Selection(
        selection=[
            ('elektronik', 'Perangkat Elektronik'),
            ('kantor', 'Peralatan Kantor'),
            ('lainnya', 'Lainnya'),
        ],
        string='Kategori',
        required=True
    )

    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('on_loan', 'On Loan'),
            ('damaged', 'Damaged'),
        ],
        string='Status',
        default='available',
        required=True
    )

    notes = fields.Text(
        string='Catatan'
    )

    def _generate_equipment_code(self, category):

        prefix = self._CATEGORY_PREFIX.get(category, 'GEN')
        pattern = f'EQ-{prefix}-'

        existing_codes = self.search([
            ('code', 'like', pattern),
        ]).mapped('code')

        max_number = 0
        for existing_code in existing_codes:
            match = re.match(rf'^{re.escape(pattern)}(\d+)$', existing_code)
            if match:
                max_number = max(max_number, int(match.group(1)))

        next_number = max_number + 1
        return f'{pattern}{next_number:03d}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New' and vals.get('category'):
                vals['code'] = self._generate_equipment_code(vals['category'])

        return super().create(vals_list)