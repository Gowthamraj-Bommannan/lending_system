from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from common.exceptions import ProjectException
from contribution.models import Contribution
from contribution.services import create_contribution, cancel_contribution
from employee.models import Employee, EmployeeRole

from .models import Loan
from .services import approve_loan, create_loan, get_available_funds, reject_loan


class LoanApiTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create_user(
            first_name='Borrower',
            last_name='One',
            email='borrower.one@hassy.in',
            password='Secret123',
            date_of_birth=date(1990, 5, 10),
        )
        self.approver = Employee.objects.create_user(
            first_name='Approver',
            last_name='One',
            email='approver.one@hassy.in',
            password='Secret123',
            date_of_birth=date(1985, 5, 10),
        )
        EmployeeRole.objects.create(employee=self.approver, role=EmployeeRole.APPROVER)
        self.admin = Employee.objects.get(email=Employee.ADMIN_EMAIL)
        self.client = APIClient()

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def request_loan(self, amount='20000.00', term_months=12):
        self.authenticate(self.employee)
        return self.client.post(
            '/api/loans/',
            {
                'requested_amount': amount,
                'request_reason': 'Home repair expenses.',
                'repayment_term_months': term_months,
            },
            format='json',
        )

    def test_request_creates_pending_loan_without_transaction_id(self):
        response = self.request_loan()

        self.assertEqual(response.status_code, 201)
        loan = Loan.objects.get(loan_id=response.data['loan_id'])
        self.assertEqual(loan.status, Loan.Status.PENDING)
        self.assertEqual(loan.request_reason, 'Home repair expenses.')
        self.assertIsNone(loan.transaction_id)
        self.assertIsNone(loan.approved_amount)
        self.assertIsNone(loan.interest_rate)
        self.assertEqual(loan.repayment_term_months, 12)

    def test_repayment_term_must_be_between_one_and_twelve_months(self):
        for term_months in (0, 13):
            response = self.request_loan(term_months=term_months)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Loan.objects.count(), 0)

    def test_employee_cannot_have_two_active_loans(self):
        first = self.request_loan()
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            '/api/loans/',
            {
                'requested_amount': '10000.00',
                'request_reason': 'Unexpected medical expenses.',
                'repayment_term_months': 12,
            },
            format='json',
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Loan.objects.filter(employee=self.employee).count(), 1)

    def test_standard_loan_list_is_always_limited_to_requesting_user(self):
        my_response = self.request_loan()
        my_loan_id = my_response.data['loan_id']
        other_loan = create_loan(
            employee=self.approver,
            requested_amount=Decimal('10000.00'),
            request_reason='Approver personal expense.',
        )

        self.authenticate(self.employee)
        employee_response = self.client.get('/api/loans/')
        self.assertEqual(
            [item['loan_id'] for item in employee_response.data],
            [my_loan_id],
        )

        self.authenticate(self.approver)
        approver_response = self.client.get('/api/loans/')
        self.assertEqual(
            [item['loan_id'] for item in approver_response.data],
            [str(other_loan.loan_id)],
        )

    def test_review_queue_shows_all_pending_and_approved_loans(self):
        pending_response = self.request_loan()
        pending_loan = Loan.objects.get(loan_id=pending_response.data['loan_id'])
        another_employee = Employee.objects.create_user(
            first_name='Borrower',
            last_name='Two',
            email='borrower.two@hassy.in',
            password='Secret123',
            date_of_birth=date(1992, 7, 15),
        )
        approved_loan = create_loan(
            employee=another_employee,
            requested_amount=Decimal('10000.00'),
            request_reason='Education costs.',
        )
        create_contribution(employee=self.employee, amount=Decimal('30000.00'))
        approve_loan(loan=approved_loan, actor=self.approver)

        self.authenticate(self.approver)
        response = self.client.get('/api/loans/review/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item['loan_id'] for item in response.data},
            {str(pending_loan.loan_id), str(approved_loan.loan_id)},
        )
        self.assertEqual(
            {item['status'] for item in response.data},
            {Loan.Status.PENDING, Loan.Status.APPROVED},
        )

    def test_employee_cannot_access_review_queue(self):
        self.authenticate(self.employee)

        response = self.client.get('/api/loans/review/')

        self.assertEqual(response.status_code, 403)

    def test_amount_outside_configured_range_is_rejected(self):
        response = self.request_loan('1000.00')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Loan.objects.count(), 0)

    def test_request_reason_is_required_and_must_not_be_blank(self):
        self.authenticate(self.employee)
        for reason in (None, '', '   '):
            payload = {
                'requested_amount': '20000.00',
                'repayment_term_months': 12,
            }
            if reason is not None:
                payload['request_reason'] = reason
            response = self.client.post('/api/loans/', payload, format='json')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Loan.objects.count(), 0)

    def test_approver_approval_reserves_funds_and_generates_transaction_id(self):
        create_contribution(employee=self.employee, amount=Decimal('30000.00'))
        response = self.request_loan('30000.00')
        loan = Loan.objects.get(loan_id=response.data['loan_id'])

        self.authenticate(self.approver)
        approval = self.client.post(
            f'/api/loans/{loan.loan_id}/approve/',
            {'approved_amount': '25000.00'},
            format='json',
        )

        self.assertEqual(approval.status_code, 200)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.APPROVED)
        self.assertEqual(loan.approved_amount, Decimal('25000.00'))
        self.assertEqual(loan.interest_rate, Decimal('10.00'))
        self.assertTrue(loan.transaction_id.startswith('LOAN-'))
        self.assertEqual(get_available_funds(), Decimal('5000.00'))

    def test_approval_rejects_amount_greater_than_request(self):
        create_contribution(employee=self.employee, amount=Decimal('30000.00'))
        response = self.request_loan('20000.00')
        loan = Loan.objects.get(loan_id=response.data['loan_id'])
        self.authenticate(self.approver)

        result = self.client.post(
            f'/api/loans/{loan.loan_id}/approve/',
            {'approved_amount': '25000.00'},
            format='json',
        )

        self.assertEqual(result.status_code, 400)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.PENDING)
        self.assertIsNone(loan.transaction_id)

    def test_approval_rejects_insufficient_funds(self):
        create_contribution(employee=self.employee, amount=Decimal('10000.00'))
        response = self.request_loan('20000.00')
        loan = Loan.objects.get(loan_id=response.data['loan_id'])
        self.authenticate(self.approver)

        result = self.client.post(f'/api/loans/{loan.loan_id}/approve/', {}, format='json')

        self.assertEqual(result.status_code, 400)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.PENDING)
        self.assertIsNone(loan.transaction_id)
        self.assertEqual(get_available_funds(), Decimal('10000.00'))

    def test_rejection_requires_and_exposes_reason(self):
        response = self.request_loan()
        loan = Loan.objects.get(loan_id=response.data['loan_id'])
        self.authenticate(self.approver)

        rejected = self.client.post(
            f'/api/loans/{loan.loan_id}/reject/',
            {'reason': 'Eligibility requirements were not met.'},
            format='json',
        )

        self.assertEqual(rejected.status_code, 200)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.REJECTED)
        self.assertIsNone(loan.transaction_id)
        self.assertEqual(rejected.data['decision_reason'], 'Eligibility requirements were not met.')

    def test_approver_cannot_decide_own_request(self):
        EmployeeRole.objects.create(employee=self.employee, role=EmployeeRole.APPROVER)
        response = self.request_loan()
        loan = Loan.objects.get(loan_id=response.data['loan_id'])

        result = self.client.post(f'/api/loans/{loan.loan_id}/reject/', {'reason': 'No'}, format='json')

        self.assertEqual(result.status_code, 400)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.PENDING)

    def test_reapplication_wait_is_two_calendar_months(self):
        Loan.objects.create(
            employee=self.employee,
            requested_amount=Decimal('10000.00'),
            request_reason='Historical test reason.',
            approved_amount=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            status=Loan.Status.COMPLETED,
            transaction_id='LOAN-OLD-TEST',
            completed_at=timezone.now() - timedelta(days=30),
        )

        response = self.request_loan()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Loan.objects.filter(employee=self.employee).count(), 1)

    def test_reapplication_is_allowed_after_two_calendar_months(self):
        Loan.objects.create(
            employee=self.employee,
            requested_amount=Decimal('10000.00'),
            request_reason='Historical test reason.',
            approved_amount=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            status=Loan.Status.COMPLETED,
            transaction_id='LOAN-OLD-ELIGIBLE',
            completed_at=timezone.now() - timedelta(days=100),
        )

        response = self.request_loan()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Loan.objects.filter(employee=self.employee).count(), 2)

    def test_cannot_cancel_contribution_needed_for_approved_loan(self):
        contribution = create_contribution(employee=self.employee, amount=Decimal('20000.00'))
        loan = create_loan(
            employee=self.employee,
            requested_amount=Decimal('10000.00'),
            request_reason='Temporary expenses.',
        )
        approve_loan(loan=loan, actor=self.approver)

        with self.assertRaises(ProjectException) as raised:
            cancel_contribution(
                contribution=contribution,
                cancelled_by=self.admin,
                reason='test cancellation',
            )

        self.assertEqual(raised.exception.code, 'contribution_cancellation_would_underfund')
        contribution.refresh_from_db()
        self.assertEqual(contribution.status, Contribution.Status.ACTIVE)

    def test_employee_cannot_approve_a_loan(self):
        create_contribution(employee=self.employee, amount=Decimal('20000.00'))
        response = self.request_loan()
        loan = Loan.objects.get(loan_id=response.data['loan_id'])

        self.authenticate(self.employee)
        result = self.client.post(
            f'/api/loans/{loan.loan_id}/approve/',
            {},
            format='json',
        )

        self.assertEqual(result.status_code, 403)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.PENDING)

    def test_funds_summary_reports_loan_adjusted_balance(self):
        create_contribution(employee=self.employee, amount=Decimal('30000.00'))
        loan = create_loan(
            employee=self.employee,
            requested_amount=Decimal('20000.00'),
            request_reason='Education expenses.',
        )
        approve_loan(loan=loan, actor=self.approver, approved_amount=Decimal('15000.00'))
        self.authenticate(self.employee)

        response = self.client.get('/api/loans/funds/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['active_contributions'], Decimal('30000.00'))
        self.assertEqual(response.data['outstanding_approved_loans'], Decimal('15000.00'))
        self.assertEqual(response.data['available_funds'], Decimal('15000.00'))
