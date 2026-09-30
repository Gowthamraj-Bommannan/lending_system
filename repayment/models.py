import uuid

from django.conf import settings
from django.db import models
from django.db.models import F
from django.utils import timezone


class Repayment(models.Model):
    repayment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    transaction_id = models.CharField(max_length=40, unique=True, editable=False)
    loan = models.ForeignKey(
        'loan.Loan',
        on_delete=models.PROTECT,
        related_name='repayments',
    )
    installment_number = models.PositiveSmallIntegerField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recorded_repayments',
    )
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=13, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'repayment'
        ordering = ('-paid_at', '-id')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(principal_amount__gt=0),
                name='repayment_principal_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(interest_amount__gte=0),
                name='repayment_interest_nonnegative',
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount=F('principal_amount') + F('interest_amount')),
                name='repayment_total_matches_components',
            ),
            models.CheckConstraint(
                condition=models.Q(installment_number__gte=1),
                name='repayment_installment_number_positive',
            ),
            models.UniqueConstraint(
                fields=('loan', 'installment_number'),
                name='unique_loan_repayment_installment',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = (
                f'REPAY-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:12].upper()}'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.transaction_id or str(self.repayment_id)
