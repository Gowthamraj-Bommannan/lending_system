import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Contribution(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CANCELLED = 'CANCELLED', 'Cancelled'

    transaction_id = models.CharField(max_length=40, unique=True, editable=False)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='contributions',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    contributed_at = models.DateTimeField(default=timezone.now)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cancelled_contributions',
        null=True,
        blank=True,
    )
    cancellation_reason = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contribution'
        ordering = ('-contributed_at', '-id')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='contribution_amount_positive',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f'CONTRIB-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:12].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.transaction_id
