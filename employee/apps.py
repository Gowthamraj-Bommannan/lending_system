import logging
from datetime import date

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model


logger = logging.getLogger(__name__)


class EmployeeConfig(AppConfig):
    name = 'employee'
    label = 'lending'
    verbose_name = 'Employee'

    def ready(self):
        post_migrate.connect(create_admin_employee, sender=self, dispatch_uid='employee.create_admin_employee')


def create_admin_employee(sender, **kwargs):
    employee_model = get_user_model()
    admin_email = employee_model.ADMIN_EMAIL
    admin_password = getattr(settings, 'ADMIN_PASSWORD', '')
    admin, created = employee_model.objects.get_or_create(
        email=admin_email,
        defaults={
            'first_name': 'Admin',
            'last_name': 'Hassy',
            'date_of_birth': date(2000, 1, 1),
            'is_active': True,
            'is_staff': True,
            'is_superuser': True,
        },
    )

    if created:
        if admin_password:
            admin.set_password(admin_password)
        else:
            admin.set_unusable_password()
    admin.first_name = 'Admin'
    admin.last_name = 'Hassy'
    admin.is_active = True
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=[
        'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'password',
    ])
    employee_role_model = sender.get_model('EmployeeRole')
    employee_role_model.objects.get_or_create(
        employee=admin,
        role=employee_role_model.ADMIN,
    )
    logger.info(
        'Administrator account bootstrap completed. event=employee.admin_bootstrap outcome=%s',
        'created' if created else 'verified',
    )
