from decimal import Decimal

from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from employee.models import EmployeeRole
from contribution.models import Contribution

from .models import Loan
from .permissions import IsActiveEmployee, IsLoanAdminOrApprover
from .serializers import (
    LoanApprovalSerializer,
    LoanRejectionSerializer,
    LoanRequestSerializer,
    LoanSerializer,
)
from .services import (
    approve_loan,
    create_loan,
    get_available_funds,
    get_outstanding_approved_loan_total,
    get_loan_installment_schedule,
    reject_loan,
)


def _can_review(user):
    return user.is_superuser or user.role_assignments.filter(
        role__in=(EmployeeRole.ADMIN, EmployeeRole.APPROVER),
    ).exists()


class LoanListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsActiveEmployee,)

    def get_serializer_class(self):
        return LoanRequestSerializer if self.request.method == 'POST' else LoanSerializer

    def get_queryset(self):
        queryset = Loan.objects.select_related(
            'employee', 'reviewed_by', 'completed_by',
        )
        return queryset.filter(employee=self.request.user)

    def create(self, request, *args, **kwargs):
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        loan = create_loan(employee=request.user, **request_serializer.validated_data)
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)


class LoanDetailView(generics.RetrieveAPIView):
    serializer_class = LoanSerializer
    permission_classes = (IsActiveEmployee,)
    lookup_field = 'loan_id'

    def get_queryset(self):
        queryset = Loan.objects.select_related('employee', 'reviewed_by', 'completed_by')
        if _can_review(self.request.user):
            return queryset
        return queryset.filter(employee=self.request.user)


class LoanInstallmentScheduleView(LoanDetailView):
    """Return the calculated schedule, current installment, and next installment."""

    def retrieve(self, request, *args, **kwargs):
        loan = self.get_object()
        return Response(get_loan_installment_schedule(loan))


class LoanReviewListView(generics.ListAPIView):
    """Expose pending and approved loans to administrators and approvers."""

    serializer_class = LoanSerializer
    permission_classes = (IsLoanAdminOrApprover,)

    def get_queryset(self):
        return Loan.objects.select_related(
            'employee', 'reviewed_by', 'completed_by',
        ).filter(
            status__in=(Loan.Status.PENDING, Loan.Status.APPROVED),
        )


class LoanFundsSummaryView(APIView):
    permission_classes = (IsActiveEmployee,)

    def get(self, request):
        available_funds = get_available_funds()
        contributed_total = Contribution.objects.filter(
            status=Contribution.Status.ACTIVE,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        outstanding_total = get_outstanding_approved_loan_total()
        return Response({
            'active_contributions': contributed_total,
            'outstanding_approved_loans': outstanding_total,
            'available_funds': available_funds,
        })


class LoanApproveView(generics.GenericAPIView):
    serializer_class = LoanApprovalSerializer
    permission_classes = (IsLoanAdminOrApprover,)
    queryset = Loan.objects.all()
    lookup_field = 'loan_id'

    def post(self, request, *args, **kwargs):
        loan = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = approve_loan(
            loan=loan,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(LoanSerializer(loan).data)


class LoanRejectView(generics.GenericAPIView):
    serializer_class = LoanRejectionSerializer
    permission_classes = (IsLoanAdminOrApprover,)
    queryset = Loan.objects.all()
    lookup_field = 'loan_id'

    def post(self, request, *args, **kwargs):
        loan = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan = reject_loan(
            loan=loan,
            actor=request.user,
            reason=serializer.validated_data['reason'],
        )
        return Response(LoanSerializer(loan).data)


