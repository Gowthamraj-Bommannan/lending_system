from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from common.constants import ErrorMessages
from common.exceptions import ProjectException


class EmployeeManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, first_name, last_name, email, password, **extra_fields):
        if not first_name:
            raise ProjectException(ErrorMessages.FIRST_NAME_REQUIRED)
        if not last_name:
            raise ProjectException(ErrorMessages.LAST_NAME_REQUIRED)

        email = self.normalize_email(email) if email else ''
        if extra_fields.get('is_superuser') and email != Employee.ADMIN_EMAIL:
            raise ProjectException(ErrorMessages.SUPERUSER_RESTRICTED)
        user = self.model(first_name=first_name, last_name=last_name, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, first_name, last_name, email=None, password=None, **extra_fields):
        extra_fields.update(is_active=True, is_staff=False, is_superuser=False)
        if not email:
            email = self.generate_email(first_name, last_name)
        return self._create_user(first_name, last_name, email, password, **extra_fields)

    def create_approver(self, first_name, last_name, email=None, password=None, **extra_fields):
        extra_fields.update(is_active=True, is_staff=True, is_superuser=False)
        if not email:
            email = self.generate_email(first_name, last_name)
        return self._create_user(first_name, last_name, email, password, **extra_fields)

    def create_superuser(self, first_name, last_name, email=None, password=None, **extra_fields):
        email = self.normalize_email(email or Employee.ADMIN_EMAIL)
        if email != Employee.ADMIN_EMAIL:
            raise ProjectException(ErrorMessages.SUPERUSER_RESTRICTED)
        extra_fields.update(is_active=True, is_staff=True, is_superuser=True)
        return self._create_user(first_name, last_name, email, password, **extra_fields)

    @staticmethod
    def generate_email(first_name, last_name):
        base = f'{first_name.strip().lower()}.{last_name.strip().lower()}@hassy.in'
        if Employee.objects.filter(email=base).exists():
            suffix = 1
            while Employee.objects.filter(email=f'{first_name.strip().lower()}.{last_name.strip().lower()}.{suffix}@hassy.in').exists():
                suffix += 1
            return f'{first_name.strip().lower()}.{last_name.strip().lower()}.{suffix}@hassy.in'
        return base


class Employee(AbstractBaseUser, PermissionsMixin):
    ADMIN_EMAIL = 'admin@hassy.in'

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    email = models.EmailField(max_length=254, unique=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EmployeeManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'employee'
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        today = timezone.localdate()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        if age < 18:
            raise ProjectException(ErrorMessages.EMPLOYEE_MINIMUM_AGE)

        if self.is_superuser:
            self.email = self.ADMIN_EMAIL
            self.is_staff = True
            self.is_active = True
            if Employee.objects.exclude(pk=self.pk).filter(is_superuser=True).exists():
                raise ProjectException(ErrorMessages.SINGLE_SUPERUSER)
        elif self.email.lower() == self.ADMIN_EMAIL:
            raise ProjectException(ErrorMessages.ADMIN_EMAIL_RESTRICTED)

        if not self.email:
            self.email = EmployeeManager.generate_email(self.first_name, self.last_name)
        else:
            base = self.email.lower()
            if '@hassy.in' in base:
                raw_prefix = base.split('@')[0]
                if '.' in raw_prefix:
                    if raw_prefix.count('.') == 1:
                        # keep user-provided email if no duplicate is being created
                        pass

        if not self.employee_id:
            last_employee = Employee.objects.exclude(employee_id='').order_by('-id').first()
            if last_employee and last_employee.employee_id:
                employee_number = last_employee.employee_id.removeprefix('EMP')
                last_number = int(employee_number) if employee_number.isdigit() else 0
                self.employee_id = f'EMP{last_number + 1:03d}'
            else:
                self.employee_id = 'EMP001'
        super().save(*args, **kwargs)


class EmployeeRole(models.Model):
    ADMIN = 'admin'
    APPROVER = 'approver'
    DEVELOPER = 'developer'
    TESTER = 'tester'
    ROLE_CHOICES = (
        (ADMIN, 'Admin'),
        (APPROVER, 'Approver'),
        (DEVELOPER, 'Developer'),
        (TESTER, 'Tester'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        db_table = 'employee_role'
        constraints = [
            models.UniqueConstraint(fields=('employee', 'role'), name='unique_employee_role'),
        ]

    def __str__(self):
        return f'{self.employee.email}: {self.role}'
