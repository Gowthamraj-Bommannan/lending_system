from rest_framework import generics, status
from rest_framework.response import Response

from .models import Repayment
from .permissions import IsActiveEmployee
from .serializers import (
    LumpSumRepaymentSerializer,
    RepaymentCreateSerializer,
    RepaymentSerializer,
)
from .services import create_lump_sum_repayment, create_repayment


class RepaymentListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsActiveEmployee,)

    def get_queryset(self):
        return Repayment.objects.select_related('loan').filter(
            recorded_by=self.request.user,
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RepaymentCreateSerializer
        return RepaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repayment = create_repayment(
            employee=request.user,
            **serializer.validated_data,
        )
        return Response(
            RepaymentSerializer(repayment).data,
            status=status.HTTP_201_CREATED,
        )


class LumpSumRepaymentView(generics.GenericAPIView):
    serializer_class = LumpSumRepaymentSerializer
    permission_classes = (IsActiveEmployee,)

    def post(self, request, loan_id, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repayment = create_lump_sum_repayment(
            employee=request.user,
            loan_id=loan_id,
            **serializer.validated_data,
        )
        return Response(
            RepaymentSerializer(repayment).data,
            status=status.HTTP_201_CREATED,
        )
