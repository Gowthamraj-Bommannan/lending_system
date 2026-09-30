from django.urls import path

from .views import (
    LoanApproveView,
    LoanDetailView,
    LoanFundsSummaryView,
    LoanInstallmentScheduleView,
    LoanListCreateView,
    LoanRejectView,
    LoanReviewListView,
)


urlpatterns = [
    path('funds/summary/', LoanFundsSummaryView.as_view(), name='loan-funds-summary'),
    path('review/', LoanReviewListView.as_view(), name='loan-review-list'),
    path('', LoanListCreateView.as_view(), name='loan-list-create'),
    path('<uuid:loan_id>/', LoanDetailView.as_view(), name='loan-detail'),
    path('<uuid:loan_id>/approve/', LoanApproveView.as_view(), name='loan-approve'),
    path('<uuid:loan_id>/reject/', LoanRejectView.as_view(), name='loan-reject'),
    path('<uuid:loan_id>/installments/', LoanInstallmentScheduleView.as_view(), name='loan-installments'),
]
