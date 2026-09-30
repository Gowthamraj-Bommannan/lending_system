from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from common.constants import ErrorMessages
from common.exceptions import ProjectException

from .authentication import EmployeeTokenSerializer
from .models import Employee, EmployeeRole
from .permissions import IsSuperAdmin
from .serializers import EmployeeCreateSerializer, EmployeeRoleSerializer, EmployeeSerializer
from .services import assign_role, deactivate_employee, remove_role


class LoginView(TokenObtainPairView):
	serializer_class = EmployeeTokenSerializer


class EmployeeListCreateView(generics.ListCreateAPIView):
	permission_classes = (IsSuperAdmin,)

	def get_serializer_class(self):
		if self.request.method == 'POST':
			return EmployeeCreateSerializer
		return EmployeeSerializer

	def get_queryset(self):
		return Employee.objects.prefetch_related('role_assignments').order_by('employee_id')


class EmployeeDetailView(generics.RetrieveUpdateAPIView):
	queryset = Employee.objects.prefetch_related('role_assignments')
	serializer_class = EmployeeSerializer
	permission_classes = (IsSuperAdmin,)
	lookup_field = 'employee_id'


class EmployeeDeactivateView(generics.GenericAPIView):
	queryset = Employee.objects.all()
	permission_classes = (IsSuperAdmin,)
	lookup_field = 'employee_id'

	def post(self, request, *args, **kwargs):
		employee = self.get_object()
		employee = deactivate_employee(employee, actor=request.user)
		return Response(EmployeeSerializer(employee).data, status=status.HTTP_200_OK)


class EmployeeRoleAssignView(generics.GenericAPIView):
	queryset = Employee.objects.all()
	serializer_class = EmployeeRoleSerializer
	permission_classes = (IsSuperAdmin,)
	lookup_field = 'employee_id'

	def post(self, request, *args, **kwargs):
		employee = self.get_object()
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		assign_role(employee, serializer.validated_data['role'], actor=request.user)
		return Response(EmployeeSerializer(employee).data, status=status.HTTP_200_OK)


class EmployeeRoleRemoveView(generics.GenericAPIView):
	queryset = Employee.objects.all()
	permission_classes = (IsSuperAdmin,)
	lookup_field = 'employee_id'

	def delete(self, request, role, *args, **kwargs):
		employee = self.get_object()
		valid_roles = {choice[0] for choice in EmployeeRole.ROLE_CHOICES}
		if role not in valid_roles:
			raise ProjectException(ErrorMessages.INVALID_ROLE)
		if role == EmployeeRole.ADMIN:
			raise ProjectException(ErrorMessages.ADMIN_ROLE_REMOVE_RESTRICTED)
		remove_role(employee, role, actor=request.user)
		return Response(EmployeeSerializer(employee).data, status=status.HTTP_200_OK)
