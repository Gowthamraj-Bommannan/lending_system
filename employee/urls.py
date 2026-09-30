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
    path('employees/', EmployeeListCreateView.as_view(), name='employee-list-create'),
    path('employees/<str:employee_id>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<str:employee_id>/deactivate/', EmployeeDeactivateView.as_view(), name='employee-deactivate'),
    path('employees/<str:employee_id>/roles/', EmployeeRoleAssignView.as_view(), name='employee-role-assign'),
    path('employees/<str:employee_id>/roles/<str:role>/', EmployeeRoleRemoveView.as_view(), name='employee-role-remove'),
]