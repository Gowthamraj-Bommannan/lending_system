from django.contrib import admin

from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'loan_id', 'transaction_id', 'employee', 'requested_amount', 'status', 'requested_at',
    )
    list_filter = ('status',)
    search_fields = ('loan_id', 'transaction_id', 'employee__employee_id', 'employee__email')
    readonly_fields = ('loan_id', 'transaction_id', 'requested_at', 'created_at', 'updated_at')
