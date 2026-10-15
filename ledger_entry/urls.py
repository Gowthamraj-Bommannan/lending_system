from django.urls import path

from .views import (
    LedgerEntryDetailView,
    LedgerEntryListView,
    LedgerSummaryView,
)


urlpatterns = [
    path('summary/', LedgerSummaryView.as_view(), name='ledger-summary'),
    path('', LedgerEntryListView.as_view(), name='ledger-entry-list'),
    path(
        '<uuid:entry_id>/',
        LedgerEntryDetailView.as_view(),
        name='ledger-entry-detail',
    ),
]