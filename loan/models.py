import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        COMPLETED = 'COMPLETED', 'Completed'

    loan_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    transaction_id = models.CharField(
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='loans',
    )
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    request_reason = models.CharField(max_length=1000)
    repayment_term_months = models.PositiveSmallIntegerField(default=12)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    requested_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reviewed_loans',
        null=True,
        blank=True,
    )
    decision_reason = models.CharField(max_length=255, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='completed_loans',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan'
        ordering = ('-requested_at', '-id')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_amount__gt=0),
                name='loan_requested_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(repayment_term_months__gte=1, repayment_term_months__lte=12),
                name='loan_term_between_1_and_12_months',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status__in=('PENDING', 'REJECTED'),
                        transaction_id__isnull=True,
                        approved_amount__isnull=True,
                        interest_rate__isnull=True,
                    )
                    | models.Q(
                        status__in=('APPROVED', 'COMPLETED'),
                        transaction_id__isnull=False,
                        approved_amount__isnull=False,
                        interest_rate__isnull=False,
                    )
                ),
                name='loan_approval_fields_match_status',
            ),
            models.UniqueConstraint(
                fields=('employee',),
                condition=models.Q(status__in=('PENDING', 'APPROVED')),
                name='one_active_loan_per_employee',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.status in (self.Status.PENDING, self.Status.REJECTED):
            self.transaction_id = None
        elif self.status in (self.Status.APPROVED, self.Status.COMPLETED) and not self.transaction_id:
            self.transaction_id = f'LOAN-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:12].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.transaction_id or str(self.loan_id)
