from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EquipmentLoanExtension(models.Model):
    _name = 'equipment.loan.extension'
    _description = 'Equipment Loan Extension Request'
    _order = 'id desc'

    name = fields.Char(
        string='Nomor Pengajuan',
        required=True,
        readonly=True,
        copy=False,
        default='New',
    )

    loan_id = fields.Many2one(
        'equipment.loan',
        string='Peminjaman',
        required=True,
        ondelete='cascade',
    )

    requested_by = fields.Many2one(
        'res.users',
        string='Diajukan Oleh',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )

    current_due_date = fields.Date(
        string='Jatuh Tempo Saat Ini',
        readonly=True,
    )

    requested_due_date = fields.Date(
        string='Jatuh Tempo Baru',
        required=True,
    )

    reason = fields.Text(
        string='Alasan Perpanjangan',
    )

    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='pending',
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'equipment.loan.extension'
                ) or 'New'
            loan_id = vals.get('loan_id')
            if loan_id:
                loan = self.env['equipment.loan'].browse(loan_id)
                if loan.exists():
                    vals['current_due_date'] = loan.due_date
        return super().create(vals_list)

    @api.constrains(
        'requested_due_date',
        'loan_id',
    )
    def _check_requested_due_date(self):
        for record in self:
            if not record.loan_id:
                continue

            if not record.requested_due_date:
                continue

            if record.requested_due_date <= record.loan_id.due_date:
                raise ValidationError(
                    'Tanggal perpanjangan harus lebih '
                    'akhir dari tanggal jatuh tempo saat ini.'
                )

    @api.constrains('loan_id')
    def _check_loan_state(self):
        for record in self:
            if record.loan_id and record.loan_id.state not in (
                    'ongoing',
                    'late',
            ):
                raise ValidationError(
                    'Perpanjangan hanya dapat diajukan untuk '
                    'peminjaman yang sedang berlangsung.'
                )

    def action_approve(self):
        for record in self:

            if record.state != 'pending':
                raise ValidationError(
                    'Hanya pengajuan dengan status Pending '
                    'yang dapat disetujui.'
                )

            loan = record.loan_id

            if loan.state not in ('ongoing', 'late'):
                raise ValidationError(
                    'Peminjaman sudah tidak dapat diperpanjang.'
                )

            for line in loan.loan_line_ids:

                existing_lines = self.env['equipment.loan.line'].search([
                    ('id', 'not in', loan.loan_line_ids.ids),
                    ('lot_id', '=', line.lot_id.id),
                    ('loan_id.state', 'in', (
                        'pending',
                        'reserved',
                        'ongoing',
                        'late',
                    )),
                    ('loan_id.loan_date', '<', record.requested_due_date),
                    ('loan_id.due_date', '>', loan.loan_date),
                ], limit=1)

                if existing_lines:
                    existing_loan = existing_lines.loan_id

                    raise ValidationError(
                        f'Serial Number "{line.lot_id.name}" '
                        f'sudah memiliki booking pada periode '
                        f'{existing_loan.loan_date} sampai '
                        f'{existing_loan.due_date}. '
                        f'Perpanjangan akan menyebabkan bentrok.'
                    )

            loan.write({
                'due_date': record.requested_due_date,
            })

            record.write({
                'state': 'approved',
            })

            template = self.env.ref(
                'equipment_loan_tracker.mail_template_equipment_loan_extension_approved'
            )
            template.send_mail(
                record.id,
                force_send=True,
            )

    def action_reject(self):
        for record in self:

            if record.state != 'pending':
                raise ValidationError(
                    'Hanya pengajuan dengan status Pending '
                    'yang dapat ditolak.'
                )

            record.write({
                'state': 'rejected',
            })

            template = self.env.ref(
                'equipment_loan_tracker.mail_template_equipment_loan_extension_rejected'
            )
            template.send_mail(
                record.id,
                force_send=True,
            )
