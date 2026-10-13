from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    EmployeeDeactivateView,
    EmployeeDetailView,
    EmployeeListCreateView,
    EmployeeRoleAssignView,
    EmployeeRoleRemoveView,
    LoginView,
)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('employee/', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('employee/<str:employee_id>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employee/<str:employee_id>/deactivate/', EmployeeDeactivateView.as_view(), name='employee-deactivate'),
    path('employee/<str:employee_id>/role/', EmployeeRoleAssignView.as_view(), name='employee-role-assign'),
    path('employee/<str:employee_id>/role/<str:role>/', EmployeeRoleRemoveView.as_view(), name='employee-role-remove'),
]