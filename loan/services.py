import calendar
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from common.constants import ErrorMessages
from common.exceptions import ProjectException
from common.lending_rules import (
    ANNUAL_INTEREST_RATE,
    MAXIMUM_LOAN_AMOUNT,
    MINIMUM_LOAN_AMOUNT,
    REAPPLICATION_WAIT_MONTHS,
)
from common.logging_utils import get_log_actor_key
from contribution.models import Contribution
from employee.models import EmployeeRole

from .models import Loan


logger = logging.getLogger(__name__)


def add_calendar_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _money(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_loan_installment_schedule(loan):
    """Calculate fixed-principal/flat-interest installments for an approved loan."""
    if loan.status not in (Loan.Status.APPROVED, Loan.Status.COMPLETED):
        raise ProjectException(
            ErrorMessages.LOAN_INSTALLMENTS_NOT_AVAILABLE,
            code='loan_installments_not_available',
        )

    start_date = loan.reviewed_at or loan.requested_at
    total_interest = _money(
        loan.approved_amount
        * loan.interest_rate
        * loan.repayment_term_months
        / Decimal('1200'),
    )
    paid_installments = set(
        loan.repayments.values_list('installment_number', flat=True),
    )
    if loan.status == Loan.Status.COMPLETED:
        paid_installments.update(range(1, loan.repayment_term_months + 1))

    installments = []
    previous_principal_total = Decimal('0.00')
    previous_interest_total = Decimal('0.00')
    for installment_number in range(1, loan.repayment_term_months + 1):
        cumulative_principal = _money(
            loan.approved_amount * installment_number / loan.repayment_term_months,
        )
        principal_due = cumulative_principal - previous_principal_total
        previous_principal_total = cumulative_principal
        cumulative_interest = _money(
            total_interest * installment_number / loan.repayment_term_months,
        )
        interest_due = cumulative_interest - previous_interest_total
        previous_interest_total = cumulative_interest
        installments.append({
            'installment_number': installment_number,
            'due_date': add_calendar_months(start_date, installment_number).date(),
            'principal_amount': principal_due,
            'interest_amount': interest_due,
            'total_amount': principal_due + interest_due,
            'status': 'PAID' if installment_number in paid_installments else 'DUE',
        })

    unpaid = [item for item in installments if item['status'] == 'DUE']
    return {
        'loan_id': loan.loan_id,
        'loan_transaction_id': loan.transaction_id,
        'status': loan.status,
        'approved_amount': loan.approved_amount,
        'annual_interest_rate': loan.interest_rate,
        'repayment_method': 'FLAT',
        'interest_calculation': 'approved_amount × annual_interest_rate × term_months ÷ 1200',
        'repayment_term_months': loan.repayment_term_months,
        'current_installment': unpaid[0] if unpaid else None,
        'next_installment': unpaid[1] if len(unpaid) > 1 else None,
        'installments': installments,
    }


def lock_fund_rows():
    # All loan approvals and contribution cancellations lock these rows in the
    # same order to avoid concurrent operations overspending the shared balance.
    list(
        Contribution.objects.select_for_update()
        .filter(status=Contribution.Status.ACTIVE)
        .order_by('pk')
        .values_list('pk', flat=True)
    )
    list(
        Loan.objects.select_for_update()
        .filter(status=Loan.Status.APPROVED)
        .order_by('pk')
        .values_list('pk', flat=True)
    )


def get_available_funds():
    active_contributions = Contribution.objects.filter(
        status=Contribution.Status.ACTIVE,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    return active_contributions - get_outstanding_approved_loan_total()


def get_outstanding_approved_loan_total():
    approved_principal = Loan.objects.filter(
        status=Loan.Status.APPROVED,
    ).aggregate(total=Sum('approved_amount'))['total'] or Decimal('0.00')
    from repayment.models import Repayment

    principal_paid = Repayment.objects.filter(
        loan__status=Loan.Status.APPROVED,
    ).aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    return approved_principal - principal_paid


def _validate_loan_amount(amount):
    if amount < MINIMUM_LOAN_AMOUNT or amount > MAXIMUM_LOAN_AMOUNT:
        raise ProjectException(
            f'Loan amount must be between {MINIMUM_LOAN_AMOUNT} and {MAXIMUM_LOAN_AMOUNT}.',
            code='invalid_loan_amount',
        )


def _validate_employee_eligibility(employee, *, exclude_loan_id=None):
    active_loans = employee.loans.filter(
        status__in=(Loan.Status.PENDING, Loan.Status.APPROVED),
    )
    if exclude_loan_id is not None:
        active_loans = active_loans.exclude(pk=exclude_loan_id)
    if active_loans.exists():
        raise ProjectException(
            ErrorMessages.EMPLOYEE_ACTIVE_LOAN_EXISTS,
            code='employee_active_loan_exists',
        )

    last_completed = employee.loans.filter(
        status=Loan.Status.COMPLETED,
        completed_at__isnull=False,
    ).order_by('-completed_at').first()
    if last_completed and last_completed.completed_at:
        eligible_at = add_calendar_months(
            last_completed.completed_at,
            REAPPLICATION_WAIT_MONTHS,
        )
        if timezone.now() < eligible_at:
            raise ProjectException(
                ErrorMessages.LOAN_REAPPLICATION_WAIT,
                code='loan_reapplication_wait',
            )


def _validate_decider(loan, actor):
    if loan.employee_id == actor.pk:
        raise ProjectException(
            ErrorMessages.LOAN_SELF_DECISION_RESTRICTED,
            code='loan_self_decision_restricted',
        )
    if not actor.is_superuser and not actor.role_assignments.filter(
        role__in=(EmployeeRole.ADMIN, EmployeeRole.APPROVER),
    ).exists():
        raise ProjectException(
            ErrorMessages.LOAN_DECISION_PERMISSION_REQUIRED,
            code='loan_decision_permission_required',
            status_code=403,
        )


@transaction.atomic
def create_loan(*, employee, requested_amount, request_reason, repayment_term_months=12):
    if not employee.is_active:
        raise ProjectException(
            ErrorMessages.EMPLOYEE_ALREADY_INACTIVE,
            code='inactive_employee_loan_request',
        )
    _validate_loan_amount(requested_amount)
    if not 1 <= repayment_term_months <= 12:
        raise ProjectException(
            ErrorMessages.LOAN_TERM_MUST_BE_1_TO_12_MONTHS,
            code='loan_term_out_of_range',
        )
    request_reason = request_reason.strip()
    if not request_reason:
        raise ProjectException(
            ErrorMessages.LOAN_REQUEST_REASON_REQUIRED,
            code='loan_request_reason_required',
        )
    employee = employee.__class__.objects.select_for_update().get(pk=employee.pk)
    _validate_employee_eligibility(employee)
    loan = Loan.objects.create(
        employee=employee,
        requested_amount=requested_amount,
        request_reason=request_reason,
        repayment_term_months=repayment_term_months,
    )
    loan_id = str(loan.loan_id)
    actor_key = get_log_actor_key(employee)
    transaction.on_commit(
        lambda: logger.info(
            'Loan request submitted successfully. event=loan.requested loan_id=%s',
            loan_id,
            extra={'actor_key': actor_key},
        ),
        robust=True,
    )
    return loan


@transaction.atomic
def approve_loan(*, loan, actor, approved_amount=None):
    lock_fund_rows()
    loan = Loan.objects.select_for_update().select_related('employee').get(pk=loan.pk)
    _validate_decider(loan, actor)
    if loan.status != Loan.Status.PENDING:
        raise ProjectException(
            ErrorMessages.LOAN_NOT_PENDING,
            code='loan_not_pending',
        )

    approved_amount = approved_amount if approved_amount is not None else loan.requested_amount
    _validate_loan_amount(approved_amount)
    if approved_amount > loan.requested_amount:
        raise ProjectException(
            ErrorMessages.LOAN_APPROVAL_EXCEEDS_REQUEST,
            code='loan_approval_exceeds_request',
        )

    available_funds = get_available_funds()
    if approved_amount > available_funds:
        raise ProjectException(
            ErrorMessages.INSUFFICIENT_AVAILABLE_FUNDS,
            code='insufficient_available_funds',
        )

    loan.approved_amount = approved_amount
    loan.interest_rate = ANNUAL_INTEREST_RATE
    loan.status = Loan.Status.APPROVED
    loan.reviewed_by = actor
    loan.reviewed_at = timezone.now()
    loan.transaction_id = f'LOAN-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:12].upper()}'
    loan.save(update_fields=(
        'approved_amount', 'interest_rate', 'status', 'reviewed_by',
        'reviewed_at', 'transaction_id', 'updated_at',
    ))
    loan_id = str(loan.loan_id)
    transaction.on_commit(
        lambda: logger.info(
            'Loan approved and funds reserved successfully. event=loan.approved loan_id=%s',
            loan_id,
            extra={'actor_key': get_log_actor_key(actor)},
        ),
        robust=True,
    )
    return loan


@transaction.atomic
def reject_loan(*, loan, actor, reason):
    loan = Loan.objects.select_for_update().select_related('employee').get(pk=loan.pk)
    _validate_decider(loan, actor)
    if loan.status != Loan.Status.PENDING:
        raise ProjectException(ErrorMessages.LOAN_NOT_PENDING, code='loan_not_pending')
    reason = reason.strip()
    if not reason:
        raise ProjectException(ErrorMessages.LOAN_REJECTION_REASON_REQUIRED, code='loan_rejection_reason_required')
    loan.status = Loan.Status.REJECTED
    loan.reviewed_by = actor
    loan.reviewed_at = timezone.now()
    loan.decision_reason = reason
    loan.save(update_fields=('status', 'reviewed_by', 'reviewed_at', 'decision_reason', 'updated_at'))
    loan_id = str(loan.loan_id)
    transaction.on_commit(
        lambda: logger.info(
            'Loan request rejected. event=loan.rejected loan_id=%s',
            loan_id,
            extra={'actor_key': get_log_actor_key(actor)},
        ),
        robust=True,
    )
    return loan


