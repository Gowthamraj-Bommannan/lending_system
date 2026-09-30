from employee.permissions import IsSuperAdmin


class IsActiveEmployeeOrAdmin(IsSuperAdmin):
    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )
