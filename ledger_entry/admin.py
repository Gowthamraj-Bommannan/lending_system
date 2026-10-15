from django.contrib import admin

from .models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = (
        'entry_id',
        'entry_type',
        'direction',
        'amount',
        'contribution',
        'loan',
        'repayment',
        'recorded_by',
        'created_at',
    )
    list_filter = ('entry_type', 'direction', 'created_at')
    search_fields = (
        'entry_id',
        'contribution__transaction_id',
        'loan__transaction_id',
        'repayment__transaction_id',
        'recorded_by__email',
    )
    readonly_fields = (
        'entry_id',
        'entry_type',
        'direction',
        'amount',
        'contribution',
        'loan',
        'repayment',
        'recorded_by',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False