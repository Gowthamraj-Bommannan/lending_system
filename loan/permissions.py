from rest_framework.permissions import BasePermission

from employee.models import EmployeeRole


class IsActiveEmployee(BasePermission):
    message = 'An active employee account is required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )


class IsLoanAdminOrApprover(BasePermission):
    message = 'Administrator or approver access is required.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        return user.role_assignments.filter(
            role__in=(EmployeeRole.ADMIN, EmployeeRole.APPROVER),
        ).exists()
