from django.contrib import admin

from .models import Contribution


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'employee', 'amount', 'status', 'contributed_at')
    list_filter = ('status',)
    search_fields = ('transaction_id', 'employee__employee_id', 'employee__email')
    readonly_fields = ('transaction_id', 'created_at', 'updated_at', 'cancelled_at', 'cancelled_by')
