from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class EquipmentLoanPortal(CustomerPortal):

    @http.route(
        ['/my/equipment-loans'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_my_equipment_loans(self, **kwargs):
        loans = request.env['equipment.loan'].search([
            ('borrower_id', '=', request.env.user.partner_id.id),
        ])
        values = {
            'loans': loans,
            'page_name': 'equipment_loans',
        }
        return request.render(
            'equipment_loan_tracker.portal_my_equipment_loans',
            values,
        )

        values = {
            'loan': loan,
            'extensions': extensions,
            'pending_extension': pending_extension,
            'page_name': 'equipment_loan',
        }

        return request.render(
            'equipment_loan_tracker.portal_my_equipment_loans',
            values,
        )

    @http.route(
        ['/my/equipment-loans/<int:loan_id>'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_equipment_loan_detail(self, loan_id, **kwargs):
        loan = request.env['equipment.loan'].browse(loan_id)

        if not loan.exists():
            return request.not_found()

        if loan.borrower_id != request.env.user.partner_id:
            return request.not_found()

        extensions = request.env[
            'equipment.loan.extension'
        ].sudo().search([
            ('loan_id', '=', loan.id),
        ], order='id desc')

        pending_extension = extensions.filtered(
            lambda extension: extension.state == 'pending'
        )[:1]

        values = {
            'loan': loan,
            'extensions': extensions,
            'pending_extension': pending_extension,
            'page_name': 'equipment_loan',
        }

        return request.render(
            'equipment_loan_tracker.portal_equipment_loan_detail',
            values,
        )

    @http.route(
        ['/my/equipment-loans/new'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_equipment_loan_new(self, **kwargs):
        products = request.env['product.product'].sudo().search([
            ('tracking', '=', 'serial'),
            ('is_damaged', '=', False),
        ])

        lots = request.env['stock.lot'].sudo().search([
            ('product_id', 'in', products.ids),
        ])

        values = {
            'products': products,
            'lots': lots,
            'page_name': 'equipment_loan_new',
        }

        return request.render(
            'equipment_loan_tracker.portal_equipment_loan_new',
            values,
        )

    @http.route(
        ['/my/equipment-loans/create'],
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def portal_equipment_loan_create(
            self,
            equipment_id,
            lot_id,
            loan_date,
            due_date,
            **kwargs,
    ):
        partner = request.env.user.partner_id

        try:
            equipment_id = int(equipment_id)
            lot_id = int(lot_id)
        except (TypeError, ValueError):
            return request.not_found()

        try:
            loan_date = fields.Date.to_date(loan_date)
            due_date = fields.Date.to_date(due_date)
        except (TypeError, ValueError):
            return request.not_found()

        if not loan_date or not due_date:
            return request.not_found()

        if due_date < loan_date:
            return request.not_found()

        equipment = request.env['product.product'].sudo().browse(
            equipment_id
        )

        lot = request.env['stock.lot'].sudo().browse(
            lot_id
        )

        if not equipment.exists() or not lot.exists():
            return request.not_found()

        if lot.product_id != equipment:
            return request.not_found()

        if equipment.tracking != 'serial':
            return request.not_found()

        if equipment.is_damaged:
            return request.not_found()

        loan = request.env['equipment.loan'].sudo().create({
            'borrower_id': partner.id,
            'loan_date': loan_date,
            'due_date': due_date,
            'loan_line_ids': [
                (0, 0, {
                    'equipment_id': equipment.id,
                    'lot_id': lot.id,
                }),
            ],
        })

        loan.write({
            'state': 'pending',
        })

        return request.redirect(
            f'/my/equipment-loans/{loan.id}'
        )

    @http.route(
        ['/my/equipment-loans/<int:loan_id>/extension'],
        type='http',
        auth='user',
        website=True,
    )
    def portal_equipment_loan_extension(self, loan_id, **kwargs):
        loan = request.env['equipment.loan'].sudo().browse(loan_id)

        if not loan.exists():
            return request.not_found()

        if loan.borrower_id != request.env.user.partner_id:
            return request.not_found()

        if loan.state not in ('ongoing', 'late'):
            return request.not_found()

        values = {
            'loan': loan,
            'page_name': 'equipment_loan_extension',
        }

        return request.render(
            'equipment_loan_tracker.portal_equipment_loan_extension',
            values,
        )

    @http.route(
        ['/my/equipment-loans/<int:loan_id>/extension/create'],
        type='http',
        auth='user',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def portal_equipment_loan_extension_create(
            self,
            loan_id,
            requested_due_date,
            reason='',
            **kwargs,
    ):
        partner = request.env.user.partner_id

        loan = request.env['equipment.loan'].sudo().browse(loan_id)

        if not loan.exists():
            return request.not_found()

        if loan.borrower_id != partner:
            return request.not_found()

        if loan.state not in ('ongoing', 'late'):
            return request.not_found()

        try:
            requested_due_date = fields.Date.to_date(
                requested_due_date
            )
        except (TypeError, ValueError):
            return request.not_found()

        if not requested_due_date:
            return request.not_found()

        if requested_due_date <= loan.due_date:
            return request.not_found()

        existing_pending = request.env[
            'equipment.loan.extension'
        ].sudo().search([
            ('loan_id', '=', loan.id),
            ('state', '=', 'pending'),
        ], limit=1)

        if existing_pending:
            return request.not_found()

        request.env['equipment.loan.extension'].sudo().create({
            'loan_id': loan.id,
            'requested_by': request.env.user.id,
            'requested_due_date': requested_due_date,
            'reason': reason,
        })

        return request.redirect(
            f'/my/equipment-loans/{loan.id}'
        )
