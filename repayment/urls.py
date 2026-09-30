from django.urls import path

from .views import RepaymentListCreateView


urlpatterns = [
    path('', RepaymentListCreateView.as_view(), name='repayment-list-create'),
]
