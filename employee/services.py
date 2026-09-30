import logging

from django.db import transaction

from .models import Employee, EmployeeRole
from common.constants import ErrorMessages
from common.exceptions import ProjectException
from common.logging_utils import get_log_actor_key


logger = logging.getLogger(__name__)


@transaction.atomic
def create_employee(*, first_name, last_name, date_of_birth, roles, actor=None):
    password = f'{first_name.capitalize()}@{date_of_birth:%Y%m%d}'
    employee = Employee.objects.create_user(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        password=password,
    )

    if EmployeeRole.APPROVER in roles:
        employee.is_staff = True
        employee.save(update_fields=('is_staff', 'updated_at'))

    EmployeeRole.objects.bulk_create([
        EmployeeRole(employee=employee, role=role) for role in roles
    ])
    employee.generated_password = password
    transaction.on_commit(
        lambda: logger.info(
            'Employee created successfully. event=employee.created target_key=%s role_count=%s',
            get_log_actor_key(employee),
            len(roles),
            extra={'actor_key': get_log_actor_key(actor)},
        ),
        robust=True,
    )
    return employee


@transaction.atomic
def deactivate_employee(employee, *, actor=None):
    if employee.email == Employee.ADMIN_EMAIL:
        raise ProjectException(ErrorMessages.ADMIN_DEACTIVATE_RESTRICTED)
    if not employee.is_active:
        raise ProjectException(ErrorMessages.EMPLOYEE_ALREADY_INACTIVE)
    employee.is_active = False
    employee.save(update_fields=('is_active', 'updated_at'))
    transaction.on_commit(
        lambda: logger.info(
            'Employee deactivated successfully. event=employee.deactivated target_key=%s',
            get_log_actor_key(employee),
            extra={'actor_key': get_log_actor_key(actor)},
        ),
        robust=True,
    )
    return employee


@transaction.atomic
def assign_role(employee, role, *, actor=None):
    if role == EmployeeRole.ADMIN:
        raise ProjectException(ErrorMessages.ADMIN_ROLE_RESTRICTED)
    role_assignment, created = EmployeeRole.objects.get_or_create(
        employee=employee,
        role=role,
    )
    if not created:
        raise ProjectException(ErrorMessages.ROLE_ALREADY_ASSIGNED)
    if role == EmployeeRole.APPROVER and not employee.is_staff:
        employee.is_staff = True
        employee.save(update_fields=('is_staff', 'updated_at'))
    transaction.on_commit(
        lambda: logger.info(
            'Employee role assigned successfully. event=employee.role_assigned target_key=%s role=%s',
            get_log_actor_key(employee),
            role,
            extra={'actor_key': get_log_actor_key(actor)},
        ),
        robust=True,
    )
    return role_assignment


@transaction.atomic
def remove_role(employee, role, *, actor=None):
    if employee.email == Employee.ADMIN_EMAIL and role == EmployeeRole.ADMIN:
        raise ProjectException(ErrorMessages.ADMIN_ROLE_REMOVE_RESTRICTED)
    role_assignment = EmployeeRole.objects.filter(employee=employee, role=role).first()
    if role_assignment is None:
        raise ProjectException(ErrorMessages.ROLE_NOT_ASSIGNED)
    role_assignment.delete()
    if role == EmployeeRole.APPROVER and not employee.role_assignments.filter(
        role=EmployeeRole.APPROVER,
    ).exists():
        employee.is_staff = False
        employee.save(update_fields=('is_staff', 'updated_at'))
    target_key = get_log_actor_key(employee)
    transaction.on_commit(
        lambda: logger.info(
            'Employee role removed successfully. event=employee.role_removed target_key=%s role=%s',
            target_key,
            role,
            extra={'actor_key': get_log_actor_key(actor)},
        ),
        robust=True,
    )