from django.urls import path

from .views import (
    ContributionCancelView,
    ContributionDetailView,
    ContributionListCreateView,
    ContributionSummaryView,
)


urlpatterns = [
    path('summary/', ContributionSummaryView.as_view(), name='contribution-summary'),
    path('', ContributionListCreateView.as_view(), name='contribution-list-create'),
    path('<str:transaction_id>/', ContributionDetailView.as_view(), name='contribution-detail'),
    path('<str:transaction_id>/cancel/', ContributionCancelView.as_view(), name='contribution-cancel'),
]
