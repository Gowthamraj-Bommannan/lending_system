from rest_framework import serializers

from common.constants import ErrorMessages
from common.exceptions import ProjectException

from .models import Contribution
from .services import create_contribution


class ContributionSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_email = serializers.EmailField(source='employee.email', read_only=True)

    class Meta:
        model = Contribution
        fields = (
            'transaction_id', 'employee_id', 'employee_email', 'amount', 'status',
            'contributed_at', 'cancelled_at', 'cancelled_by', 'cancellation_reason',
            'reference', 'remarks', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'transaction_id', 'employee_id', 'employee_email', 'status', 'contributed_at',
            'cancelled_at', 'cancelled_by', 'cancellation_reason', 'created_at', 'updated_at',
        )

    def create(self, validated_data):
        request = self.context['request']
        return create_contribution(employee=request.user, **validated_data)


class ContributionCancelSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(max_length=255, required=True)

    def validate_cancellation_reason(self, reason):
        if not reason.strip():
            raise ProjectException(ErrorMessages.CANCELLATION_REASON_REQUIRED)
        return reason.strip()
