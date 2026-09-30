import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from common.constants import ErrorMessages
from common.exceptions import ProjectException
from common.logging_utils import get_log_actor_key
from loan.models import Loan
from loan.services import get_loan_installment_schedule, lock_fund_rows

from .models import Repayment


logger = logging.getLogger(__name__)


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

    # Keep lock ordering consistent with loan approvals and contribution
    # cancellations. This serializes repayment against other fund mutations.
    lock_fund_rows()
    try:
        loan = Loan.objects.select_for_update().get(loan_id=loan_id)
    except Loan.DoesNotExist as exc:
        raise ProjectException(
            ErrorMessages.REPAYMENT_LOAN_NOT_FOUND,
            status_code=404,
            code='repayment_loan_not_found',
        ) from exc

    if loan.employee_id != employee.pk:
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

    principal_paid = loan.repayments.aggregate(total=Sum('principal_amount'))['total'] or Decimal('0.00')
    remaining_principal = loan.approved_amount - principal_paid
    if principal_amount > remaining_principal:
        raise ProjectException(
            ErrorMessages.REPAYMENT_PRINCIPAL_EXCEEDS_REMAINING,
            code='repayment_principal_exceeds_remaining',
        )

    repayment = Repayment.objects.create(
        loan=loan,
        recorded_by=employee,
        installment_number=installment_number,
        principal_amount=principal_amount,
        interest_amount=interest_amount,
        total_amount=total_amount,
    )
    principal_paid += principal_amount
    if installment_number == loan.repayment_term_months:
        loan.status = Loan.Status.COMPLETED
        loan.completed_at = timezone.now()
        loan.completed_by = employee
        loan.save(update_fields=('status', 'completed_at', 'completed_by', 'updated_at'))
        event_name = 'repayment.created.loan_completed'
        message = 'Final principal repayment recorded; loan completed successfully.'
    else:
        event_name = 'repayment.created'
        message = 'Repayment recorded successfully.'

    transaction.on_commit(
        lambda: logger.info(
            '%s event=%s repayment_transaction_id=%s loan_id=%s',
            message,
            event_name,
            repayment.transaction_id,
            loan.loan_id,
            extra={'actor_key': get_log_actor_key(employee)},
        ),
        robust=True,
    )
    return repayment
