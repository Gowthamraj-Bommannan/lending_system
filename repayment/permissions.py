from rest_framework.permissions import BasePermission


class IsActiveEmployee(BasePermission):
    message = 'An active employee account is required.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )
