from decimal import Decimal

from django.db.models import Q, Sum

from .models import LedgerEntry


def _create_entry(*, entry_type, direction, amount, recorded_by, **source):
    if amount < Decimal('0.00'):
        raise ValueError('Ledger entry amount cannot be negative.')
    if amount == Decimal('0.00'):
        return None

    return LedgerEntry.objects.create(
        entry_type=entry_type,
        direction=direction,
        amount=amount,
        recorded_by=recorded_by,
        **source,
    )


def record_contribution_credit(*, contribution, actor):
    return _create_entry(
        entry_type=LedgerEntry.EntryType.CONTRIBUTION_CREDIT,
        direction=LedgerEntry.Direction.CREDIT,
        amount=contribution.amount,
        contribution=contribution,
        recorded_by=actor,
    )


def record_contribution_reversal(*, contribution, actor):
    return _create_entry(
        entry_type=LedgerEntry.EntryType.CONTRIBUTION_REVERSAL,
        direction=LedgerEntry.Direction.DEBIT,
        amount=contribution.amount,
        contribution=contribution,
        recorded_by=actor,
    )


def record_loan_reservation(*, loan, actor):
    return _create_entry(
        entry_type=LedgerEntry.EntryType.LOAN_RESERVATION,
        direction=LedgerEntry.Direction.DEBIT,
        amount=loan.approved_amount,
        loan=loan,
        recorded_by=actor,
    )


def record_repayment_entries(*, repayment, actor):
    entries = []
    for entry_type, amount in (
        (LedgerEntry.EntryType.REPAYMENT_PRINCIPAL, repayment.principal_amount),
        (LedgerEntry.EntryType.REPAYMENT_INTEREST, repayment.interest_amount),
    ):
        entry = _create_entry(
            entry_type=entry_type,
            direction=LedgerEntry.Direction.CREDIT,
            amount=amount,
            repayment=repayment,
            recorded_by=actor,
        )
        if entry is not None:
            entries.append(entry)
    return entries


def get_ledger_summary():
    totals = LedgerEntry.objects.aggregate(
        credits=Sum(
            'amount',
            filter=Q(direction=LedgerEntry.Direction.CREDIT),
        ),
        debits=Sum(
            'amount',
            filter=Q(direction=LedgerEntry.Direction.DEBIT),
        ),
    )

    credits = totals['credits'] or Decimal('0.00')
    debits = totals['debits'] or Decimal('0.00')

    return {
        'total_credits': credits,
        'total_debits': debits,
        'net_balance': credits - debits,
        'entry_count': LedgerEntry.objects.count(),
    }