from rest_framework import permissions

from common.exceptions import ProjectException

from .models import EmployeeRole


def _is_authenticated(request):
    return bool(
        request.user
        and request.user.is_authenticated
        and request.user.is_active
    )


class IsSuperAdmin(permissions.BasePermission):
    message = 'Super administrator access is required.'

    def has_permission(self, request, view):
        return _is_authenticated(request) and request.user.is_superuser


def HasRole(role):
    """Return a permission class requiring one role."""
    valid_roles = {choice[0] for choice in EmployeeRole.ROLE_CHOICES}
    if role not in valid_roles:
        raise ProjectException(f'Unknown employee role: {role}')

    class RolePermission(permissions.BasePermission):
        message = f'The {role} role is required.'

        def has_permission(self, request, view):
            return (
                _is_authenticated(request)
                and request.user.role_assignments.filter(role=role).exists()
            )

    RolePermission.__name__ = f'Has{role.title()}Role'
    return RolePermission


def HasAnyRole(*roles):
    """Return a permission class requiring at least one supplied role."""
    valid_roles = {choice[0] for choice in EmployeeRole.ROLE_CHOICES}
    invalid_roles = set(roles) - valid_roles
    if invalid_roles:
        raise ProjectException(f'Unknown employee role: {sorted(invalid_roles)[0]}')
    if not roles:
        raise ProjectException('At least one employee role is required.')

    class AnyRolePermission(permissions.BasePermission):
        message = 'At least one required employee role is missing.'

        def has_permission(self, request, view):
            return (
                _is_authenticated(request)
                and request.user.role_assignments.filter(role__in=roles).exists()
            )

    AnyRolePermission.__name__ = 'HasAnyEmployeeRole'
    return AnyRolePermission