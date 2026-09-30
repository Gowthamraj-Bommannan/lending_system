from decimal import Decimal
import logging

from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from common.constants import ErrorMessages
from common.exceptions import ProjectException
from common.lending_rules import MAXIMUM_CONTRIBUTION, MINIMUM_CONTRIBUTION
from common.logging_utils import get_log_actor_key

from .models import Contribution


logger = logging.getLogger(__name__)


def validate_contribution_amount(amount):
    if amount < MINIMUM_CONTRIBUTION or amount > MAXIMUM_CONTRIBUTION:
        raise ProjectException(
            f'Contribution amount must be between {MINIMUM_CONTRIBUTION} and {MAXIMUM_CONTRIBUTION}.',
            code='invalid_contribution_amount',
        )


def validate_employee_contribution_capacity(employee, amount):
    current_total = employee.contributions.filter(
        status=Contribution.Status.ACTIVE,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    remaining_capacity = MAXIMUM_CONTRIBUTION - current_total
    if amount > remaining_capacity:
        raise ProjectException(
            ErrorMessages.EMPLOYEE_CONTRIBUTION_LIMIT_EXCEEDED.format(
                current_total=current_total,
                remaining_capacity=remaining_capacity,
                maximum_contribution=MAXIMUM_CONTRIBUTION,
            ),
            code='employee_contribution_limit_exceeded',
        )


@transaction.atomic
def create_contribution(*, employee, amount, reference='', remarks=''):
    validate_contribution_amount(amount)

    # Serialize concurrent writes for this employee so two requests cannot both
    # consume the same remaining capacity.
    employee = employee.__class__.objects.select_for_update().get(pk=employee.pk)
    validate_employee_contribution_capacity(employee, amount)

    contribution = Contribution.objects.create(
        employee=employee,
        amount=amount,
        reference=reference,
        remarks=remarks,
    )
    transaction_id = contribution.transaction_id
    actor_key = get_log_actor_key(employee)
    transaction.on_commit(
        lambda: logger.info(
            'Contribution record created successfully. event=contribution.created '
            'transaction_id=%s owner_key=%s',
            transaction_id,
            actor_key,
            extra={'actor_key': actor_key},
        ),
        robust=True,
    )
    return contribution


@transaction.atomic
def cancel_contribution(*, contribution, cancelled_by, reason):
    # A contribution cannot be removed if it would leave approved loans
    # underfunded. Use the same lock ordering as loan approval/completion.
    from loan.services import get_outstanding_approved_loan_total, lock_fund_rows

    lock_fund_rows()
    contribution = Contribution.objects.select_for_update().get(pk=contribution.pk)
    if contribution.status == Contribution.Status.CANCELLED:
        raise ProjectException(
            ErrorMessages.CONTRIBUTION_ALREADY_CANCELLED,
            code='contribution_already_cancelled',
        )
    active_contributions = Contribution.objects.filter(
        status=Contribution.Status.ACTIVE,
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    if active_contributions - contribution.amount < get_outstanding_approved_loan_total():
        raise ProjectException(
            ErrorMessages.CONTRIBUTION_CANCELLATION_WOULD_UNDERFUND,
            code='contribution_cancellation_would_underfund',
        )
    contribution.status = Contribution.Status.CANCELLED
    contribution.cancelled_at = timezone.now()
    contribution.cancelled_by = cancelled_by
    contribution.cancellation_reason = reason
    contribution.save(update_fields=(
        'status', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'updated_at',
    ))
    transaction_id = contribution.transaction_id
    owner_key = get_log_actor_key(contribution.employee)
    transaction.on_commit(
        lambda: logger.info(
            'Contribution cancelled successfully. event=contribution.cancelled '
            'transaction_id=%s owner_key=%s status=ACTIVE->CANCELLED',
            transaction_id,
            owner_key,
            extra={'actor_key': get_log_actor_key(cancelled_by)},
        ),
        robust=True,
    )
    return contribution


def get_contribution_summary(queryset):
    active_contributions = queryset.filter(status=Contribution.Status.ACTIVE)
    totals = active_contributions.aggregate(total_amount=models.Sum('amount'))
    total_contributed = totals['total_amount'] or Decimal('0.00')
    from loan.services import get_available_funds

    return {
        'total_contributed': total_contributed,
        'available_funds': get_available_funds(),
        'active_contribution_count': active_contributions.count(),
        'cancelled_contribution_count': queryset.filter(
            status=Contribution.Status.CANCELLED,
        ).count(),
    }
