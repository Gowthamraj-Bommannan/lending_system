API_OPERATIONS = {
    ('login', 'POST'): ('Employee login', 'api.auth.login'),
    ('token-refresh', 'POST'): ('Authentication token refresh', 'api.auth.token_refresh'),
    ('employee-list-create', 'GET'): ('Employee list retrieval', 'api.employee.list'),
    ('employee-list-create', 'POST'): ('Employee creation', 'api.employee.create'),
    ('employee-detail', 'GET'): ('Employee detail retrieval', 'api.employee.retrieve'),
    ('employee-detail', 'PUT'): ('Employee detail update', 'api.employee.update'),
    ('employee-detail', 'PATCH'): ('Employee detail update', 'api.employee.update'),
    ('employee-deactivate', 'POST'): ('Employee deactivation', 'api.employee.deactivate'),
    ('employee-role-assign', 'POST'): ('Employee role assignment', 'api.employee.role.assign'),
    ('employee-role-remove', 'DELETE'): ('Employee role removal', 'api.employee.role.remove'),
    ('contribution-list-create', 'GET'): ('Contribution list retrieval', 'api.contribution.list'),
    ('contribution-list-create', 'POST'): ('Contribution creation', 'api.contribution.create'),
    ('contribution-summary', 'GET'): ('Contribution summary retrieval', 'api.contribution.summary'),
    ('contribution-detail', 'GET'): ('Contribution detail retrieval', 'api.contribution.retrieve'),
    ('contribution-cancel', 'POST'): ('Contribution cancellation', 'api.contribution.cancel'),
    ('loan-list-create', 'GET'): ('Loan list retrieval', 'api.loan.list'),
    ('loan-list-create', 'POST'): ('Loan request submission', 'api.loan.request'),
    ('loan-review-list', 'GET'): ('Pending and approved loan review list retrieval', 'api.loan.review.list'),
    ('loan-detail', 'GET'): ('Loan detail retrieval', 'api.loan.retrieve'),
    ('loan-installments', 'GET'): ('Loan installment schedule retrieval', 'api.loan.installments'),
    ('loan-funds-summary', 'GET'): ('Available funds summary retrieval', 'api.loan.funds.summary'),
    ('loan-approve', 'POST'): ('Loan approval', 'api.loan.approve'),
    ('loan-reject', 'POST'): ('Loan rejection', 'api.loan.reject'),
    ('repayment-list-create', 'GET'): ('Repayment list retrieval', 'api.repayment.list'),
    ('repayment-list-create', 'POST'): ('Loan repayment submission', 'api.repayment.create'),
}

PROJECT_ERROR_LOG_MESSAGES = {
    'invalid_contribution_amount': (
        'Contribution creation was rejected because the amount is outside the permitted range.'
    ),
    'employee_contribution_limit_exceeded': (
        'Contribution creation was rejected because the employee active-contribution limit would be exceeded.'
    ),
    'contribution_already_cancelled': (
        'Contribution cancellation was rejected because it is already cancelled.'
    ),
    'invalid_loan_amount': 'Loan request or approval was rejected because the amount is outside the permitted range.',
    'loan_term_out_of_range': 'Loan request was rejected because the repayment term must be between 1 and 12 months.',
    'loan_installments_not_available': 'Loan installment schedule is unavailable because the loan is not approved or completed.',
    'employee_active_loan_exists': 'Loan request was rejected because the employee already has an active loan.',
    'loan_reapplication_wait': 'Loan request was rejected because the employee is within the reapplication waiting period.',
    'loan_not_pending': 'Loan decision was rejected because the loan is not pending.',
    'loan_approval_exceeds_request': 'Loan approval was rejected because the approved amount exceeds the request.',
    'insufficient_available_funds': 'Loan approval was rejected because available funds are insufficient.',
    'loan_self_decision_restricted': 'Loan decision was rejected because employees cannot decide their own requests.',
    'loan_decision_permission_required': 'Loan decision was rejected because administrator or approver access is required.',
    'loan_rejection_reason_required': 'Loan rejection was refused because a reason is required.',
    'loan_request_reason_required': 'Loan request was rejected because a request reason is required.',
    'loan_not_approved': 'Loan completion was rejected because the loan is not approved.',
    'inactive_employee_loan_request': 'Loan request was rejected because the employee account is inactive.',
    'contribution_cancellation_would_underfund': 'Contribution cancellation was rejected because it would leave approved loans underfunded.',
    'repayment_loan_not_found': 'Repayment was rejected because the referenced loan was not found.',
    'repayment_loan_not_owned': 'Repayment was rejected because the loan belongs to another employee.',
    'repayment_loan_not_approved': 'Repayment was rejected because the loan is not approved.',
    'repayment_principal_must_be_positive': 'Repayment was rejected because principal must be greater than zero.',
    'repayment_interest_cannot_be_negative': 'Repayment was rejected because interest cannot be negative.',
    'repayment_total_mismatch': 'Repayment was rejected because total does not equal principal plus interest.',
    'repayment_principal_exceeds_remaining': 'Repayment was rejected because principal exceeds the remaining loan balance.',
    'repayment_installment_out_of_order': 'Repayment was rejected because installments must be paid in order.',
    'repayment_amount_does_not_match_installment': 'Repayment was rejected because amounts do not match the scheduled installment.',
}


def get_api_operation(request):
    """Return a safe action description and event prefix for the API request."""
    resolver_match = getattr(request, 'resolver_match', None)
    route_name = getattr(resolver_match, 'url_name', None)
    method = getattr(request, 'method', '').upper()
    operation = API_OPERATIONS.get((route_name, method))
    if operation:
        return operation

    route_operations = [
        value for (name, _method), value in API_OPERATIONS.items()
        if name == route_name
    ]
    if not route_operations:
        return 'API request', 'api.request'
    if method == 'HEAD':
        return API_OPERATIONS.get((route_name, 'GET'), route_operations[0])
    if method == 'OPTIONS':
        route_operation, event_prefix = route_operations[0]
        return f'{route_operation} metadata retrieval', f'{event_prefix}.options'
    return route_operations[0]
