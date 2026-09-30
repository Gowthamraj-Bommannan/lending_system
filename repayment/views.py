from rest_framework import generics, status
from rest_framework.response import Response

from .models import Repayment
from .permissions import IsActiveEmployee
from .serializers import RepaymentCreateSerializer, RepaymentSerializer
from .services import create_repayment


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
