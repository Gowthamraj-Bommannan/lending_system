from rest_framework import status


class ErrorMessages:
    REQUEST_FAILED = 'The request could not be completed.'
    VALIDATION_FAILED = 'Request validation failed.'
    AUTHENTICATION_REQUIRED = 'Authentication is required.'
    PERMISSION_DENIED = 'You do not have permission to perform this action.'
    RESOURCE_NOT_FOUND = 'The requested resource was not found.'
    UNEXPECTED_ERROR = 'An unexpected error occurred. Please try again later.'
    FIRST_NAME_REQUIRED = 'The first_name field is required.'
    LAST_NAME_REQUIRED = 'The last_name field is required.'
    EMPLOYEE_MINIMUM_AGE = 'Employee must be at least 18 years old.'
    ADMIN_ROLE_RESTRICTED = 'The admin role cannot be assigned through this endpoint.'
    SUPERUSER_RESTRICTED = 'The only permitted superuser is admin@hassy.in.'
    SINGLE_SUPERUSER = 'Only one superuser is allowed.'
    ADMIN_EMAIL_RESTRICTED = 'admin@hassy.in is reserved for the superuser.'
    EMPLOYEE_ALREADY_INACTIVE = 'Employee is already inactive.'
    ADMIN_DEACTIVATE_RESTRICTED = 'The admin employee cannot be deactivated.'
    ADMIN_ROLE_REMOVE_RESTRICTED = 'The admin role cannot be removed from the admin employee.'
    ROLE_ALREADY_ASSIGNED = 'This role is already assigned to the employee.'
    ROLE_NOT_ASSIGNED = 'This role is not assigned to the employee.'
    INVALID_ROLE = 'The requested role is not valid.'
    CONTRIBUTION_ALREADY_CANCELLED = 'This contribution is already cancelled.'
    CANCELLATION_REASON_REQUIRED = 'A cancellation reason is required.'
    INVALID_CONTRIBUTION_RANGE = 'Minimum contribution cannot exceed maximum contribution.'
    INVALID_LOAN_RANGE = 'Minimum loan amount cannot exceed maximum loan amount.'
    EMPLOYEE_CONTRIBUTION_LIMIT_EXCEEDED = (
        'The employee has already contributed {current_total}. '
        'Remaining allowed contribution is {remaining_capacity}. '
        'Total active contributions cannot exceed {maximum_contribution}.'
    )
    EMPLOYEE_ACTIVE_LOAN_EXISTS = 'The employee already has a pending or approved loan.'
    LOAN_REAPPLICATION_WAIT = 'The employee must wait two calendar months after completing a loan before applying again.'
    LOAN_NOT_PENDING = 'Only pending loan requests can be approved or rejected.'
    LOAN_APPROVAL_EXCEEDS_REQUEST = 'Approved amount cannot exceed the requested amount.'
    INSUFFICIENT_AVAILABLE_FUNDS = 'Available funds are insufficient for this loan approval.'
    LOAN_SELF_DECISION_RESTRICTED = 'Employees cannot approve or reject their own loan requests.'
    LOAN_DECISION_PERMISSION_REQUIRED = 'Administrator or approver access is required to decide loans.'
    LOAN_REJECTION_REASON_REQUIRED = 'A reason is required when rejecting a loan.'
    LOAN_REQUEST_REASON_REQUIRED = 'A reason is required when requesting a loan.'
    LOAN_AMOUNT_RANGE = 'Loan amount must be between the configured minimum and maximum.'
    LOAN_TERM_MUST_BE_1_TO_12_MONTHS = 'Loan repayment term must be between 1 and 12 months.'
    LOAN_INSTALLMENTS_NOT_AVAILABLE = 'Installments are available only for approved or completed loans.'
    CONTRIBUTION_CANCELLATION_WOULD_UNDERFUND = 'This contribution cannot be cancelled because approved loans depend on the funds.'
    REPAYMENT_LOAN_NOT_FOUND = 'The requested loan was not found.'
    REPAYMENT_LOAN_NOT_OWNED = 'Only the employee who owns the loan can make its repayment.'
    REPAYMENT_LOAN_NOT_APPROVED = 'Repayments can only be made for approved loans that are not yet completed.'
    REPAYMENT_PRINCIPAL_MUST_BE_POSITIVE = 'Principal repayment must be greater than zero.'
    REPAYMENT_INTEREST_CANNOT_BE_NEGATIVE = 'Interest amount cannot be negative.'
    REPAYMENT_TOTAL_MUST_MATCH_COMPONENTS = 'Total repayment must equal principal plus interest.'
    REPAYMENT_PRINCIPAL_EXCEEDS_REMAINING = 'Principal repayment cannot exceed the loan remaining principal.'
    REPAYMENT_INSTALLMENTS_MUST_BE_PAID_IN_ORDER = 'Loan installments must be paid in order; submit the current unpaid installment.'
    REPAYMENT_AMOUNT_MUST_MATCH_INSTALLMENT = 'Repayment principal, interest, and total must match the scheduled installment.'


class ErrorStatus:
    BAD_REQUEST = status.HTTP_400_BAD_REQUEST
    UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED
    FORBIDDEN = status.HTTP_403_FORBIDDEN
    NOT_FOUND = status.HTTP_404_NOT_FOUND
    INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR


STATUS_MESSAGES = {
    ErrorStatus.BAD_REQUEST: ErrorMessages.VALIDATION_FAILED,
    ErrorStatus.UNAUTHORIZED: ErrorMessages.AUTHENTICATION_REQUIRED,
    ErrorStatus.FORBIDDEN: ErrorMessages.PERMISSION_DENIED,
    ErrorStatus.NOT_FOUND: ErrorMessages.RESOURCE_NOT_FOUND,
    ErrorStatus.INTERNAL_SERVER_ERROR: ErrorMessages.UNEXPECTED_ERROR,
}