from django.contrib import admin

from .models import Repayment


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'loan', 'payment_type', 'installment_number', 'recorded_by', 'principal_amount',
        'interest_amount', 'total_amount', 'paid_at',
    )
    search_fields = ('repayment_id', 'loan__transaction_id', 'recorded_by__employee_id')
    readonly_fields = ('repayment_id', 'created_at')

    def has_delete_permission(self, request, obj=None):
        return False
