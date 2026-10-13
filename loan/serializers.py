from rest_framework import serializers

from .models import Loan, LoanReview


class LoanRequestSerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    request_reason = serializers.CharField(max_length=1000, required=True, allow_blank=False, trim_whitespace=True)
    repayment_term_months = serializers.IntegerField(min_value=1, max_value=12)


class LoanReviewSerializer(serializers.ModelSerializer):
    reviewed_by_employee_id = serializers.CharField(
        source='reviewed_by_employee.employee_id',
        read_only=True,
    )

    class Meta:
        model = LoanReview
        fields = (
            'decision', 'reviewed_by_employee_id', 'reviewed_at', 'decision_reason',
            'approved_amount', 'interest_rate',
        )


class LoanSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(source='borrower_employee.employee_id', read_only=True)
    employee_email = serializers.EmailField(source='borrower_employee.email', read_only=True)
    reviewed_by_employee_id = serializers.CharField(
        source='reviewed_by_employee.employee_id',
        read_only=True,
        allow_null=True,
    )
    completed_by_employee_id = serializers.CharField(
        source='completed_by_employee.employee_id',
        read_only=True,
        allow_null=True,
    )
    review_history = LoanReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = (
            'loan_id', 'transaction_id', 'employee_id', 'employee_email',
            'requested_amount', 'request_reason', 'repayment_term_months',
            'approved_amount', 'interest_rate', 'status',
            'requested_at', 'reviewed_at', 'reviewed_by_employee_id',
            'decision_reason', 'review_history', 'completed_at', 'completed_by_employee_id',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


# class LoanApprovalSerializer(serializers.Serializer):
#     approved_amount = serializers.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         required=False,
#     )


# class LoanRejectionSerializer(serializers.Serializer):
#     reason = serializers.CharField(max_length=255, required=True, allow_blank=False, trim_whitespace=True)


class LoanDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=('approve', 'reject'))
    approved_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    reason = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=False,
        trim_whitespace=True
    )

    def validate(self, attrs):
        action = attrs['action']

        if action == 'approve':
            if 'reason' in attrs:
                raise serializers.ValidationError(
                    {
                        'reason': 'Reason not required for approving a loan.'
                    }
                )
        elif action == 'reject':
            if 'approved_amount' in attrs:
                raise serializers.ValidationError(
                    {
                        'approved_amount': 'Approved amount not required for rejecting a loan.'
                    }
                )

            if 'reason' not in attrs:
                raise serializers.ValidationError(
                    {
                        'reason': 'Reason is required for rejecting a loan.'
                    }
                )
        return attrs