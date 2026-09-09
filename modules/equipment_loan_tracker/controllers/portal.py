from odoo import http
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

        values = {
            'loan': loan,
            'page_name': 'equipment_loan',
        }

        return request.render(
            'equipment_loan_tracker.portal_equipment_loan_detail',
            values,
        )
