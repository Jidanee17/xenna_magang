from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class EquipmentLoan(models.Model):
    _name = 'equipment.loan'
    _description = 'Equipment Loan'
    _order = 'loan_date desc, id desc'

    name = fields.Char(
        string='Nomor Peminjaman',
        required=True,
        readonly=True,
        copy=False,
        default='New'
    )

    borrower_id = fields.Many2one(
        'res.partner',
        string='Peminjam',
        required=True,
        ondelete='restrict'
    )

    type = fields.Selection(
        selection=[
            ('internal', 'Internal Staff'),
            ('external', 'Eksternal'),
        ],
        string='Tipe',
    )

    loan_line_ids = fields.One2many(
        'equipment.loan.line',
        'loan_id',
        string='Daftar Alat'
    )

    borrower_email = fields.Char(
        string='Email',
        related='borrower_id.email',
        readonly=True
    )

    borrower_phone = fields.Char(
        string='Phone',
        related='borrower_id.phone',
        readonly=True
    )

    loan_duration = fields.Integer(
        string='Durasi Peminjaman (Hari)',
        compute='_compute_loan_duration'
    )

    loan_date = fields.Date(
        string='Tanggal Peminjaman',
        required=True,
        default=fields.Date.context_today
    )

    due_date = fields.Date(
        string='Tanggal Jatuh Tempo',
        required=True
    )

    return_date = fields.Date(
        string='Tanggal Pengembalian'
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('ongoing', 'Ongoing'),
            ('returned', 'Returned'),
            ('late', 'Late'),
            ('lost', 'Lost'),
        ],
        string='Status',
        default='draft',
        required=True
    )

    line_notes = fields.Text(
        string='Catatan'
    )

    equipment_names = fields.Char(
        string='Daftar Alat',
        compute='_compute_equipment_names'
    )

    picking_ids = fields.One2many(
        'stock.picking',
        'loan_id',
        string='Stock Pickings'
    )

    picking_count = fields.Integer(
        string='Jumlah Picking',
        compute='_compute_picking_count'
    )

    invoice_ids = fields.One2many(
        'account.move',
        'loan_id',
        string='Invoice Denda'
    )

    invoice_count = fields.Integer(
        string='Jumlah Invoice',
        compute='_compute_invoice_count'
    )

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'equipment.loan'
                ) or 'New'

        return super().create(vals_list)

    @api.constrains('loan_date', 'due_date')
    def _check_due_date(self):
        for record in self:
            if record.loan_date and record.due_date:
                if record.due_date < record.loan_date:
                    raise ValidationError(
                        'Tanggal jatuh tempo tidak boleh lebih awal '
                        'dari tanggal peminjaman.'
                    )

    @api.constrains('return_date', 'loan_date')
    def _check_return_date(self):
        for record in self:
            if record.return_date and record.loan_date:
                if record.return_date < record.loan_date:
                    raise ValidationError(
                        'Tanggal pengembalian tidak boleh lebih awal '
                        'dari tanggal peminjaman.'
                    )

    @api.constrains('loan_line_ids', 'state')
    def _check_double_booking(self):
        for record in self:
            if record.state not in ('ongoing', 'late'):
                continue

            for line in record.loan_line_ids:
                existing_lines = self.env['equipment.loan.line'].search([
                    ('id', '!=', line.id),
                    ('equipment_id', '=', line.equipment_id.id),
                    ('loan_id.state', 'in', ('ongoing', 'late')),
                ], limit=1)

                if existing_lines:
                    raise ValidationError(
                        f'Alat "{line.equipment_id.name}" sedang dipinjam '
                        'dan tidak dapat dipinjam kembali.'
                    )

    def _get_loan_location(self):
        """Lokasi internal khusus untuk barang yang sedang dipinjam."""
        location = self.env.ref(
            'equipment_loan_tracker.stock_location_loan',
            raise_if_not_found=False
        )
        if not location:
            raise UserError(
                'Lokasi stok "Peminjaman" belum dikonfigurasi. '
                'Silakan install ulang module ini.'
            )
        return location

    def _get_internal_picking_type(self):
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.env.company.id),
        ], limit=1)
        if not picking_type:
            raise UserError(
                'Tidak ditemukan tipe operasi Internal Transfer. '
                'Pastikan module Inventory sudah dikonfigurasi dengan benar.'
            )
        return picking_type

    def _create_and_validate_picking(self, src_location, dest_location):
        self.ensure_one()
        picking_type = self._get_internal_picking_type()

        move_lines = [(0, 0, {
            'name': line.equipment_id.name,
            'product_id': line.equipment_id.id,
            'product_uom_qty': 1,
            'product_uom': line.equipment_id.uom_id.id,
            'location_id': src_location.id,
            'location_dest_id': dest_location.id,
        }) for line in self.loan_line_ids]

        picking = self.env['stock.picking'].create({
            'partner_id': self.borrower_id.id,
            'picking_type_id': picking_type.id,
            'location_id': src_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.name,
            'loan_id': self.id,
            'move_ids': move_lines,
        })

        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()

        return picking

    def action_confirm(self):
        for record in self:

            if not record.loan_line_ids:
                raise ValidationError(
                    'Minimal harus ada satu alat yang dipinjam.'
                )

            if record.due_date < record.loan_date:
                raise ValidationError(
                    'Tanggal jatuh tempo tidak boleh lebih awal '
                    'dari tanggal peminjaman.'
                )

            picking_type = record._get_internal_picking_type()
            src_location = picking_type.default_location_src_id
            loan_location = record._get_loan_location()

            for line in record.loan_line_ids:

                if line.equipment_id.is_damaged:
                    raise ValidationError(
                        f'Alat "{line.equipment_id.name}" dalam kondisi '
                        'rusak dan tidak dapat dipinjam.'
                    )

                available_qty = line.equipment_id.with_context(
                    location=src_location.id
                ).qty_available

                if available_qty < 1:
                    raise ValidationError(
                        f'Alat "{line.equipment_id.name}" tidak tersedia '
                        'di stok (quantity available = 0).'
                    )

            record._create_and_validate_picking(src_location, loan_location)

            record.write({'state': 'ongoing'})

    def action_return(self):
        for record in self:

            if record.state not in ('ongoing', 'late'):
                raise ValidationError(
                    'Hanya peminjaman yang sedang berlangsung '
                    'atau terlambat yang dapat dikembalikan.'
                )

            today = fields.Date.context_today(self)

            picking_type = record._get_internal_picking_type()
            dest_location = picking_type.default_location_src_id
            loan_location = record._get_loan_location()

            record._create_and_validate_picking(loan_location, dest_location)

            if today > record.due_date:
                new_state = 'late'
                note = (
                    'Peminjaman dikembalikan setelah '
                    'tanggal jatuh tempo.'
                )
            else:
                new_state = 'returned'
                note = False

            record.write({
                'state': new_state,
                'return_date': today,
                'line_notes': note,
            })

    def action_lost(self):

        for record in self:

            if record.state not in ('ongoing', 'late'):
                raise ValidationError(
                    'Hanya peminjaman yang sedang berlangsung atau '
                    'terlambat yang dapat dinyatakan hilang.'
                )

            invoice_lines = []
            for line in record.loan_line_ids:
                product = line.equipment_id
                penalty = product.penalty_amount or product.list_price

                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': penalty,
                    'name': f'Denda kehilangan alat: {product.name}',
                }))

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': record.borrower_id.id,
                'invoice_origin': record.name,
                'loan_id': record.id,
                'invoice_line_ids': invoice_lines,
            })
            invoice.action_post()

            record.write({'state': 'lost'})

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'stock.action_picking_tree_all'
        )
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        action['context'] = {}
        return action

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type'
        )
        action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        action['context'] = {}
        return action

    @api.model
    def _cron_check_overdue(self):
        today = fields.Date.context_today(self)

        loans = self.search([
            ('state', '=', 'ongoing'),
            ('due_date', '<', today),
        ])

        if loans:
            loans.write({
                'state': 'late',
                'line_notes': 'kamu sudah terlambat'
            })

    @api.depends('loan_date', 'return_date')
    def _compute_loan_duration(self):
        today = fields.Date.context_today(self)

        for record in self:
            if not record.loan_date:
                record.loan_duration = 0
                continue

            end_date = record.return_date or today
            duration = (end_date - record.loan_date).days

            record.loan_duration = max(duration, 0)

    @api.depends('loan_line_ids.equipment_id')
    def _compute_equipment_names(self):
        for record in self:
            record.equipment_names = ', '.join(
                record.loan_line_ids.mapped('equipment_id.name')
            )


class EquipmentLoanLine(models.Model):
    _name = 'equipment.loan.line'
    _description = 'Equipment Loan Line'

    loan_id = fields.Many2one(
        'equipment.loan',
        string='Peminjaman',
        required=True,
        ondelete='cascade'
    )

    equipment_id = fields.Many2one(
        'product.product',
        string='Alat',
        required=True,
        ondelete='restrict',
        domain=[('is_storable', '=', True)],
    )
