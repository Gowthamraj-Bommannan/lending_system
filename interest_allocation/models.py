from django.conf import settings
from django.db import models
from django.db.models import Q

class InterestAllocationBatch(models.Model):
    period_start = models.DateField()
    period_end = models.DateField()
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='interest_allocations_batches'
        )
    source_interest_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )
    allocated_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)

