from django.contrib import admin

from .models import Loan, LoanReview


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        'loan_id', 'transaction_id', 'borrower_employee', 'requested_amount', 'status', 'requested_at',
    )
    list_filter = ('status',)
    search_fields = (
        'loan_id', 'transaction_id',
        'borrower_employee__employee_id', 'borrower_employee__email',
    )
    readonly_fields = ('loan_id', 'transaction_id', 'requested_at', 'created_at', 'updated_at')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoanReview)
class LoanReviewAdmin(admin.ModelAdmin):
    list_display = ('loan', 'decision', 'reviewed_by_employee', 'reviewed_at')
    list_filter = ('decision',)
    search_fields = ('loan__transaction_id', 'reviewed_by_employee__employee_id')
    readonly_fields = (
        'loan', 'reviewed_by_employee', 'decision', 'reviewed_at',
        'decision_reason', 'approved_amount', 'interest_rate',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
