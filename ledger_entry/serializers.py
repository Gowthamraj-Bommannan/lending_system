from rest_framework import serializers
from .models import LedgerEntry

class LedgerEntrySerializer(serializers.ModelSerializer):

    contribution_transaction_id = serializers.CharField(
        source='contribution.transaction_id',
        read_only=True,
        allow_null=True,
    )
    loan_transaction_id = serializers.CharField(
        source='loan.transaction_id',
        read_only=True,
        allow_null=True,
    )
    repayment_transaction_id = serializers.CharField(
        source='repayment.transaction_id',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = LedgerEntry
        fields = (
            'entry_id',
            'entry_type',
            'direction',
            'amount',
            'contribution_transaction_id',
            'loan_transaction_id',
            'repayment_transaction_id',
            'recorded_by',
            'created_at',
        )
        read_only_fields = fields