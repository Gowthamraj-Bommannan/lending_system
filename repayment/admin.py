from django.contrib import admin

from .models import Repayment


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = (
        'repayment_id', 'loan', 'recorded_by', 'principal_amount',
        'interest_amount', 'total_amount', 'paid_at',
    )
    search_fields = ('repayment_id', 'loan__transaction_id', 'recorded_by__employee_id')
    readonly_fields = ('repayment_id', 'created_at')
