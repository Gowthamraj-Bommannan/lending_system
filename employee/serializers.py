from django.utils import timezone
from rest_framework import serializers

from common.constants import ErrorMessages
from common.exceptions import ProjectException
from .models import Employee, EmployeeRole


class EmployeeCreateSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=[choice[0] for choice in EmployeeRole.ROLE_CHOICES]),
        write_only=True,
    )
    generated_password = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = (
            'first_name', 'last_name', 'date_of_birth', 'roles', 'email',
            'employee_id', 'generated_password',
        )
        read_only_fields = ('email', 'employee_id')

    def validate_roles(self, roles):
        if EmployeeRole.ADMIN in roles:
            raise ProjectException(ErrorMessages.ADMIN_ROLE_RESTRICTED)
        if not roles:
            raise ProjectException(ErrorMessages.VALIDATION_FAILED)
        return list(dict.fromkeys(roles))

    def validate_date_of_birth(self, date_of_birth):
        today = timezone.localdate()
        age = today.year - date_of_birth.year - (
            (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
        )
        if age < 18:
            raise ProjectException(ErrorMessages.EMPLOYEE_MINIMUM_AGE)
        return date_of_birth

    def create(self, validated_data):
        from .services import create_employee

        return create_employee(actor=self.context['request'].user, **validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['roles'] = list(instance.role_assignments.values_list('role', flat=True))
        return representation


class EmployeeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            'first_name', 'last_name', 'date_of_birth', 'email',
            'employee_id', 'is_active', 'is_staff', 'is_superuser', 'roles',
        )
        read_only_fields = (
            'email', 'employee_id', 'is_active', 'is_staff', 'is_superuser', 'roles',
        )

    def get_roles(self, employee):
        return list(employee.role_assignments.values_list('role', flat=True))

    def validate_date_of_birth(self, date_of_birth):
        today = timezone.localdate()
        age = today.year - date_of_birth.year - (
            (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
        )
        if age < 18:
            raise ProjectException(ErrorMessages.EMPLOYEE_MINIMUM_AGE)
        return date_of_birth


class EmployeeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[choice[0] for choice in EmployeeRole.ROLE_CHOICES],
    )

    def validate_role(self, role):
        if role == EmployeeRole.ADMIN:
            raise ProjectException(ErrorMessages.ADMIN_ROLE_RESTRICTED)
        return role