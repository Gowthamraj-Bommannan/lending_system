import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class LedgerEntryQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Ledger entries are immutable.')

    def delete(self):
        raise ValidationError('Ledger entries cannot be deleted.')


class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CONTRIBUTION_CREDIT = 'CONTRIBUTION_CREDIT', 'Contribution credit'
        CONTRIBUTION_REVERSAL = 'CONTRIBUTION_REVERSAL', 'Contribution reversal'
        LOAN_RESERVATION = 'LOAN_RESERVATION', 'Loan fund reservation'
        REPAYMENT_PRINCIPAL = 'REPAYMENT_PRINCIPAL', 'Loan principal repayment'
        REPAYMENT_INTEREST = 'REPAYMENT_INTEREST', 'Loan interest repayment'

    class Direction(models.TextChoices):
        CREDIT = 'CREDIT', 'Credit'
        DEBIT = 'DEBIT', 'Debit'

    entry_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    entry_type = models.CharField(
        max_length=30,
        choices=EntryType.choices,
    )
    direction = models.CharField(
        max_length=6,
        choices=Direction.choices,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    contribution = models.ForeignKey(
        'contribution.Contribution',
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        null=True,
        blank=True,
    )
    loan = models.ForeignKey(
        'loan.Loan',
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        null=True,
        blank=True,
    )
    repayment = models.ForeignKey(
        'repayment.Repayment',
        on_delete=models.PROTECT,
        related_name='ledger_entries',
        null=True,
        blank=True,
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recorded_ledger_entries',
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = models.Manager.from_queryset(LedgerEntryQuerySet)()

    class Meta:
        db_table = 'ledger_entry'
        ordering = ('-created_at', '-id')
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='ledger_amount_positive',
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        entry_type__in=(
                            'CONTRIBUTION_CREDIT',
                            'CONTRIBUTION_REVERSAL',
                        ),
                        contribution__isnull=False,
                        loan__isnull=True,
                        repayment__isnull=True,
                    )
                    | Q(
                        entry_type='LOAN_RESERVATION',
                        contribution__isnull=True,
                        loan__isnull=False,
                        repayment__isnull=True,
                    )
                    | Q(
                        entry_type__in=(
                            'REPAYMENT_PRINCIPAL',
                            'REPAYMENT_INTEREST',
                        ),
                        contribution__isnull=True,
                        loan__isnull=True,
                        repayment__isnull=False,
                    )
                ),
                name='ledger_entry_source_matches_type',
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        entry_type='CONTRIBUTION_CREDIT',
                        direction='CREDIT',
                    )
                    | Q(
                        entry_type='CONTRIBUTION_REVERSAL',
                        direction='DEBIT',
                    )
                    | Q(
                        entry_type='LOAN_RESERVATION',
                        direction='DEBIT',
                    )
                    | Q(
                        entry_type='REPAYMENT_PRINCIPAL',
                        direction='CREDIT',
                    )
                    | Q(
                        entry_type='REPAYMENT_INTEREST',
                        direction='CREDIT',
                    )
                ),
                name='ledger_direction_matches_type',
            ),
            models.UniqueConstraint(
                fields=('contribution', 'entry_type'),
                condition=Q(contribution__isnull=False),
                name='ledger_unique_contribution_type',
            ),
            models.UniqueConstraint(
                fields=('loan', 'entry_type'),
                condition=Q(loan__isnull=False),
                name='ledger_unique_loan_type',
            ),
            models.UniqueConstraint(
                fields=('repayment', 'entry_type'),
                condition=Q(repayment__isnull=False),
                name='ledger_unique_repayment_type',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError('Ledger entries are immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Ledger entries cannot be deleted.')

    def __str__(self):
        return f'{self.entry_type}: {self.amount} ({self.direction})'