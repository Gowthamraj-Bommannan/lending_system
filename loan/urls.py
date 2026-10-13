from django.urls import path
from repayment.views import LumpSumRepaymentView

from .views import (
    LoanApproveView,
    LoanDetailView,
    LoanFundsSummaryView,
    LoanInstallmentScheduleView,
    LoanListCreateView,
    LoanNextInstallmentView,
    LoanRejectView,
    LoanReviewListView,
)


urlpatterns = [
    path('fund/summary/', LoanFundsSummaryView.as_view(), name='loan-funds-summary'),
    path('review/', LoanReviewListView.as_view(), name='loan-review-list'),
    path('', LoanListCreateView.as_view(), name='loan-list-create'),
    path('<uuid:loan_id>/', LoanDetailView.as_view(), name='loan-detail'),
    path('<uuid:loan_id>/approve/', LoanApproveView.as_view(), name='loan-approve'),
    path('<uuid:loan_id>/reject/', LoanRejectView.as_view(), name='loan-reject'),
    path('<uuid:loan_id>/installment/', LoanInstallmentScheduleView.as_view(), name='loan-installments'),
    path('<uuid:loan_id>/installment/next/', LoanNextInstallmentView.as_view(), name='loan-next-installment'),
    path('<uuid:loan_id>/repayment/lump-sum/', LumpSumRepaymentView.as_view(), name='loan-lump-sum-repayment'),
]
