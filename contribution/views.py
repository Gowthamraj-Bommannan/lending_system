from rest_framework import generics, status
from rest_framework.response import Response

from common.exceptions import ProjectException
from employee.permissions import IsSuperAdmin

from .models import Contribution
from .permissions import IsActiveEmployeeOrAdmin
from .serializers import ContributionCancelSerializer, ContributionSerializer
from .services import cancel_contribution, get_contribution_summary


class ContributionListCreateView(generics.ListCreateAPIView):
    serializer_class = ContributionSerializer
    permission_classes = (IsActiveEmployeeOrAdmin,)

    def get_queryset(self):
        queryset = Contribution.objects.select_related('employee', 'cancelled_by')
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(employee=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'summary': get_contribution_summary(queryset),
            'contributions': serializer.data,
        })


class ContributionSummaryView(generics.GenericAPIView):
    permission_classes = (IsActiveEmployeeOrAdmin,)

    def get_queryset(self):
        queryset = Contribution.objects.all()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(employee=self.request.user)

    def get(self, request, *args, **kwargs):
        return Response(get_contribution_summary(self.get_queryset()))


class ContributionDetailView(generics.RetrieveAPIView):
    serializer_class = ContributionSerializer
    permission_classes = (IsActiveEmployeeOrAdmin,)
    lookup_field = 'transaction_id'

    def get_queryset(self):
        queryset = Contribution.objects.select_related('employee', 'cancelled_by')
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(employee=self.request.user)


class ContributionCancelView(generics.GenericAPIView):
    serializer_class = ContributionCancelSerializer
    permission_classes = (IsSuperAdmin,)
    queryset = Contribution.objects.select_related('employee', 'cancelled_by')
    lookup_field = 'transaction_id'

    def post(self, request, *args, **kwargs):
        contribution = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contribution = cancel_contribution(
            contribution=contribution,
            cancelled_by=request.user,
            reason=serializer.validated_data['cancellation_reason'],
        )
        return Response(ContributionSerializer(contribution).data, status=status.HTTP_200_OK)
