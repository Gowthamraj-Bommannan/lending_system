import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from common.constants import ErrorMessages
from common.exceptions import ProjectException
from common.logging_utils import get_log_actor_key
from loan.models import Loan
from loan.services import (
    get_loan_installment_schedule,
    get_total_contract_interest,
    lock_fund_rows,
)

from .models import Repayment


logger = logging.getLogger(__name__)


def _get_owned_approved_loan(*, employee, loan_id):
    try:
        loan = Loan.objects.select_for_update().get(loan_id=loan_id)
    except Loan.DoesNotExist as exc:
        raise ProjectException(
            ErrorMessages.REPAYMENT_LOAN_NOT_FOUND,
            status_code=404,
            code='repayment_loan_not_found',
        ) from exc

    if loan.borrower_employee_id != employee.pk:
        raise ProjectException(
            ErrorMessages.REPAYMENT_LOAN_NOT_OWNED,
            status_code=403,
            code='repayment_loan_not_owned',
        )
    if loan.status != Loan.Status.APPROVED:
        raise ProjectException(
            ErrorMessages.REPAYMENT_LOAN_NOT_APPROVED,
            code='repayment_loan_not_approved',
        )
    return loan


def _record_success(repayment, employee, *, message, event_name):
    transaction.on_commit(
        lambda: logger.info(
            '%s event=%s repayment_transaction_id=%s loan_id=%s',
            message,
            event_name,
            repayment.transaction_id,
            repayment.loan.loan_id,
            extra={'actor_key': get_log_actor_key(employee)},
        ),
        robust=True,
    )


def _complete_loan_if_fully_paid(loan, employee):
    principal_paid = loan.repayments.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    interest_paid = loan.repayments.aggregate(total=Sum('interest_amount'))['total'] or Decimal('0.00')
    if (
        principal_paid == loan.approved_amount
        and interest_paid == get_total_contract_interest(loan)
    ):
        loan.status = Loan.Status.COMPLETED
        loan.completed_at = timezone.now()
        loan.completed_by_employee = employee
        loan.save(update_fields=('status', 'completed_at', 'completed_by_employee', 'updated_at'))
        return True
    return False


@transaction.atomic
def create_repayment(
    *,
    employee,
    loan_id,
    installment_number,
    principal_amount,
    interest_amount,
    total_amount,
):
    if principal_amount <= 0:
        raise ProjectException(
            ErrorMessages.REPAYMENT_PRINCIPAL_MUST_BE_POSITIVE,
            code='repayment_principal_must_be_positive',
        )
    if interest_amount < 0:
        raise ProjectException(
            ErrorMessages.REPAYMENT_INTEREST_CANNOT_BE_NEGATIVE,
            code='repayment_interest_cannot_be_negative',
        )
    if total_amount != principal_amount + interest_amount:
        raise ProjectException(
            ErrorMessages.REPAYMENT_TOTAL_MUST_MATCH_COMPONENTS,
            code='repayment_total_mismatch',
        )

    lock_fund_rows()
    loan = _get_owned_approved_loan(employee=employee, loan_id=loan_id)
    schedule = get_loan_installment_schedule(loan)
    current_installment = schedule['current_installment']
    if current_installment is None or installment_number != current_installment['installment_number']:
        raise ProjectException(
            ErrorMessages.REPAYMENT_INSTALLMENTS_MUST_BE_PAID_IN_ORDER,
            code='repayment_installment_out_of_order',
        )
    if (
        principal_amount != current_installment['principal_amount']
        or interest_amount != current_installment['interest_amount']
        or total_amount != current_installment['total_amount']
    ):
        raise ProjectException(
            ErrorMessages.REPAYMENT_AMOUNT_MUST_MATCH_INSTALLMENT,
            code='repayment_amount_does_not_match_installment',
        )

    repayment = Repayment.objects.create(
        loan=loan,
        recorded_by=employee,
        installment_number=installment_number,
        payment_type=Repayment.PaymentType.INSTALLMENT,
        principal_amount=principal_amount,
        interest_amount=interest_amount,
        total_amount=total_amount,
    )
    completed = _complete_loan_if_fully_paid(loan, employee)
    if completed:
        message = 'Final principal repayment recorded; loan completed successfully.'
        event_name = 'repayment.created.loan_completed'
    else:
        message = 'Repayment recorded successfully.'
        event_name = 'repayment.created'
    _record_success(repayment, employee, message=message, event_name=event_name)
    return repayment


@transaction.atomic
def create_lump_sum_repayment(
    *,
    employee,
    loan_id,
    principal_amount,
    interest_amount,
    total_amount,
):
    if principal_amount < 0:
        raise ProjectException(
            ErrorMessages.REPAYMENT_PRINCIPAL_CANNOT_BE_NEGATIVE,
            code='repayment_principal_cannot_be_negative',
        )
    if interest_amount < 0:
        raise ProjectException(
            ErrorMessages.REPAYMENT_INTEREST_CANNOT_BE_NEGATIVE,
            code='repayment_interest_cannot_be_negative',
        )
    if total_amount <= 0 or total_amount != principal_amount + interest_amount:
        raise ProjectException(
            ErrorMessages.REPAYMENT_TOTAL_MUST_MATCH_COMPONENTS,
            code='repayment_total_mismatch',
        )

    lock_fund_rows()
    loan = _get_owned_approved_loan(employee=employee, loan_id=loan_id)
    schedule = get_loan_installment_schedule(loan)
    unpaid_installments = [
        installment for installment in schedule['installments']
        if installment['status'] == 'DUE'
    ]
    remaining_principal = sum(
        (installment['principal_amount'] for installment in unpaid_installments),
        Decimal('0.00'),
    )
    remaining_interest = sum(
        (installment['interest_amount'] for installment in unpaid_installments),
        Decimal('0.00'),
    )
    if principal_amount > remaining_principal or interest_amount > remaining_interest:
        raise ProjectException(
            ErrorMessages.LUMP_SUM_AMOUNT_EXCEEDS_BALANCE,
            code='lump_sum_amount_exceeds_balance',
        )
    if principal_amount == remaining_principal and interest_amount != remaining_interest:
        raise ProjectException(
            ErrorMessages.LUMP_SUM_MUST_CLEAR_INTEREST_WITH_FINAL_PRINCIPAL,
            code='lump_sum_must_clear_interest_with_final_principal',
        )

    repayment = Repayment.objects.create(
        loan=loan,
        recorded_by=employee,
        installment_number=None,
        payment_type=Repayment.PaymentType.LUMP_SUM,
        principal_amount=principal_amount,
        interest_amount=interest_amount,
        total_amount=total_amount,
    )
    completed = _complete_loan_if_fully_paid(loan, employee)
    if completed:
        message = 'Lump-sum payoff recorded; loan completed successfully.'
        event_name = 'repayment.lump_sum.loan_completed'
    else:
        message = 'Lump-sum repayment recorded; remaining installments recalculated.'
        event_name = 'repayment.lump_sum.created'
    _record_success(repayment, employee, message=message, event_name=event_name)
    return repayment
