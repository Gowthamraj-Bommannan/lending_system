from decimal import Decimal

from rest_framework import serializers

from common.constants import ErrorMessages
from common.exceptions import ProjectException

from .models import Repayment


class RepaymentCreateSerializer(serializers.Serializer):
    loan_id = serializers.UUIDField()
    installment_number = serializers.IntegerField(min_value=1)
    principal_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal('0.00'),
    )
    total_amount = serializers.DecimalField(max_digits=13, decimal_places=2)

    def validate(self, attrs):
        principal_amount = attrs['principal_amount']
        interest_amount = attrs['interest_amount']
        if principal_amount <= 0:
            raise ProjectException(
                ErrorMessages.REPAYMENT_PRINCIPAL_MUST_BE_POSITIVE,
                code='repayment_principal_must_be_positive',
            )
        if interest_amount < 0:
            raise ProjectException(
                ErrorMessages.REPAYMENT_INTEREST_CANNOT_BE_NEGATIVE,
                code='repayment_interest_cannot_be_negative',
            )
        if attrs['total_amount'] != principal_amount + interest_amount:
            raise ProjectException(
                ErrorMessages.REPAYMENT_TOTAL_MUST_MATCH_COMPONENTS,
                code='repayment_total_mismatch',
            )
        return attrs


class RepaymentSerializer(serializers.ModelSerializer):
    loan_id = serializers.UUIDField(source='loan.loan_id', read_only=True)
    loan_transaction_id = serializers.CharField(source='loan.transaction_id', read_only=True)

    class Meta:
        model = Repayment
        fields = (
            'repayment_id', 'transaction_id', 'loan_id', 'loan_transaction_id', 'principal_amount',
            'installment_number', 'interest_amount', 'total_amount', 'paid_at',
        )
        read_only_fields = fields
