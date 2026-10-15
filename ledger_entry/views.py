from rest_framework import generics
from rest_framework.response import Response

from .models import LedgerEntry
from .permissions import IsSuperAdminLedgerReader
from .serializers import LedgerEntrySerializer
from .services import get_ledger_summary


class LedgerEntryListView(generics.ListAPIView):
    serializer_class = LedgerEntrySerializer
    permission_classes = (IsSuperAdminLedgerReader,)

    def get_queryset(self):
        return LedgerEntry.objects.select_related(
            'contribution',
            'loan',
            'repayment',
            'recorded_by',
        )


class LedgerEntryDetailView(generics.RetrieveAPIView):
    serializer_class = LedgerEntrySerializer
    permission_classes = (IsSuperAdminLedgerReader,)
    lookup_field = 'entry_id'
    lookup_url_kwarg = 'entry_id'

    def get_queryset(self):
        return LedgerEntry.objects.select_related(
            'contribution',
            'loan',
            'repayment',
            'recorded_by',
        )


class LedgerSummaryView(generics.GenericAPIView):
    permission_classes = (IsSuperAdminLedgerReader,)

    def get(self, request, *args, **kwargs):
        return Response(get_ledger_summary())