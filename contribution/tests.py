from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase
from rest_framework.test import APIClient

from common.exceptions import ProjectException
from common.lending_rules import MAXIMUM_CONTRIBUTION
from contribution.models import Contribution
from contribution.services import create_contribution
from employee.models import Employee


class ContributionServiceTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create_user(
            first_name='Asha',
            last_name='Nair',
            email='asha.nair@hassy.in',
            password='Secret123',
            date_of_birth=date(1995, 5, 10),
        )

    def test_employee_cannot_exceed_total_active_contribution_cap(self):
        create_contribution(employee=self.employee, amount=Decimal('20000.00'))

        with self.assertRaises(ProjectException) as raised:
            create_contribution(employee=self.employee, amount=Decimal('40000.00'))
        self.assertEqual(raised.exception.code, 'employee_contribution_limit_exceeded')

        total_active = self.employee.contributions.filter(
            status=Contribution.Status.ACTIVE,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        self.assertEqual(total_active, Decimal('20000.00'))

    def test_employee_can_fill_remaining_capacity_without_exceeding_cap(self):
        create_contribution(employee=self.employee, amount=Decimal('30000.00'))
        create_contribution(employee=self.employee, amount=Decimal('20000.00'))

        total_active = self.employee.contributions.filter(
            status=Contribution.Status.ACTIVE,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        self.assertEqual(total_active, MAXIMUM_CONTRIBUTION)

        with self.assertRaises(ProjectException):
            create_contribution(employee=self.employee, amount=Decimal('100.00'))

    def test_api_response_includes_request_correlation_id(self):
        response = self.client.get('/api/contributions/summary/')

        self.assertEqual(response.status_code, 401)
        self.assertTrue(response['X-Request-ID'])

    def test_successful_api_request_logs_meaningful_message(self):
        client = APIClient()
        client.force_authenticate(user=self.employee)

        with self.assertLogs('common.middleware', level='INFO') as captured:
            response = client.get('/api/contributions/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(
            'Contribution summary retrieval completed successfully.' in message
            for message in captured.output
        ))

    def test_contribution_cap_failure_logs_specific_safe_message(self):
        create_contribution(employee=self.employee, amount=Decimal('20000.00'))
        client = APIClient()
        client.force_authenticate(user=self.employee)

        with self.assertLogs('common.exceptions', level='WARNING') as captured:
            response = client.post(
                '/api/contributions/',
                {'amount': '40000.00'},
                format='json',
            )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(any(
            'Contribution creation was rejected because the employee active-contribution limit would be exceeded.' in message
            for message in captured.output
        ))
        self.assertFalse(any('20000.00' in message or '40000.00' in message for message in captured.output))

    def test_employee_api_permission_failure_logs_endpoint_specific_message(self):
        client = APIClient()
        client.force_authenticate(user=self.employee)

        with self.assertLogs('common.exceptions', level='WARNING') as captured:
            response = client.get('/api/employees/')

        self.assertEqual(response.status_code, 403)
        self.assertTrue(any(
            'Employee list retrieval was rejected because the actor lacks permission.' in message
            and 'event=api.employee.list.failed reason=permission_denied' in message
            for message in captured.output
        ))
