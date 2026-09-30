from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from contribution.models import Contribution
from contribution.services import create_contribution
from employee.models import Employee
from loan.models import Loan
from loan.services import (
    approve_loan,
    create_loan,
    get_available_funds,
    get_loan_installment_schedule,
    reject_loan,
)

from .models import Repayment


class RepaymentApiTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create_user(
            first_name='Repayer',
            last_name='One',
            email='repayer.one@hassy.in',
            password='Secret123',
            date_of_birth=date(1990, 5, 10),
        )
        self.other_employee = Employee.objects.create_user(
            first_name='Repayer',
            last_name='Two',
            email='repayer.two@hassy.in',
            password='Secret123',
            date_of_birth=date(1992, 5, 10),
        )
        self.admin = Employee.objects.get(email=Employee.ADMIN_EMAIL)
        self.client = APIClient()

    def authenticate(self, employee=None):
        self.client.force_authenticate(user=employee or self.employee)

    def make_approved_loan(
        self,
        *,
        employee=None,
        amount=Decimal('12000.00'),
        term_months=12,
    ):
        employee = employee or self.employee
        create_contribution(employee=employee, amount=Decimal('30000.00'))
        loan = create_loan(
            employee=employee,
            requested_amount=amount,
            request_reason='Repayment test loan.',
            repayment_term_months=term_months,
        )
        return approve_loan(loan=loan, actor=self.admin)

    def post_repayment(
        self,
        *,
        loan,
        installment_number=None,
        principal=None,
        interest=None,
        total=None,
    ):
        current = (
            get_loan_installment_schedule(loan)['current_installment']
            if loan.status in (Loan.Status.APPROVED, Loan.Status.COMPLETED)
            else None
        )
        installment_number = installment_number or (
            current['installment_number'] if current else 1
        )
        principal = current['principal_amount'] if principal is None and current else Decimal(principal or '0.00')
        interest = current['interest_amount'] if interest is None and current else Decimal(interest or '0.00')
        total = principal + interest if total is None else Decimal(total)
        self.authenticate(loan.employee)
        return self.client.post(
            '/api/repayments/',
            {
                'loan_id': str(loan.loan_id),
                'installment_number': installment_number,
                'principal_amount': str(principal),
                'interest_amount': str(interest),
                'total_amount': str(total),
            },
            format='json',
        )

    def test_partial_repayment_records_components_and_releases_principal_funds(self):
        loan = self.make_approved_loan()
        self.assertEqual(get_available_funds(), Decimal('18000.00'))

        response = self.post_repayment(loan=loan)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['transaction_id'].startswith('REPAY-'))
        repayment = Repayment.objects.get(repayment_id=response.data['repayment_id'])
        self.assertEqual(repayment.transaction_id, response.data['transaction_id'])
        self.assertEqual(repayment.installment_number, 1)
        self.assertEqual(repayment.principal_amount, Decimal('1000.00'))
        self.assertEqual(repayment.interest_amount, Decimal('100.00'))
        self.assertEqual(repayment.total_amount, Decimal('1100.00'))
        self.assertEqual(get_available_funds(), Decimal('19000.00'))
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.APPROVED)

        schedule_response = self.client.get(f'/api/loans/{loan.loan_id}/installments/')
        self.assertEqual(schedule_response.status_code, 200)
        self.assertEqual(schedule_response.data['current_installment']['installment_number'], 2)
        self.assertEqual(schedule_response.data['next_installment']['installment_number'], 3)

    def test_final_principal_payment_completes_loan_and_releases_funds(self):
        loan = self.make_approved_loan(amount=Decimal('12000.00'), term_months=12)
        for installment_number in range(1, 12):
            response = self.post_repayment(loan=loan, installment_number=installment_number)
            self.assertEqual(response.status_code, 201)

        response = self.post_repayment(loan=loan, installment_number=12)

        self.assertEqual(response.status_code, 201)
        loan.refresh_from_db()
        self.assertEqual(loan.status, Loan.Status.COMPLETED)
        self.assertIsNotNone(loan.completed_at)
        self.assertEqual(loan.completed_by_id, self.employee.pk)
        self.assertEqual(get_available_funds(), Decimal('30000.00'))

    def test_installment_schedule_matches_flat_interest_example(self):
        loan = self.make_approved_loan(amount=Decimal('30000.00'), term_months=12)
        self.authenticate(self.employee)

        response = self.client.get(f'/api/loans/{loan.loan_id}/installments/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['repayment_method'], 'FLAT')
        self.assertIn('term_months', response.data['interest_calculation'])
        self.assertEqual(response.data['repayment_term_months'], 12)
        current = response.data['current_installment']
        self.assertEqual(current['installment_number'], 1)
        self.assertEqual(current['principal_amount'], Decimal('2500.00'))
        self.assertEqual(current['interest_amount'], Decimal('250.00'))
        self.assertEqual(current['total_amount'], Decimal('2750.00'))
        self.assertEqual(response.data['next_installment']['installment_number'], 2)
        self.assertEqual(response.data['next_installment']['total_amount'], Decimal('2750.00'))

    def test_schedule_rounding_remainder_is_adjusted_in_final_installment(self):
        loan = self.make_approved_loan(amount=Decimal('10000.00'), term_months=3)

        schedule = get_loan_installment_schedule(loan)['installments']

        self.assertEqual(
            [row['principal_amount'] for row in schedule],
            [Decimal('3333.33'), Decimal('3333.34'), Decimal('3333.33')],
        )
        self.assertEqual(
            [row['interest_amount'] for row in schedule],
            [Decimal('83.33'), Decimal('83.34'), Decimal('83.33')],
        )
        self.assertEqual(
            sum((row['principal_amount'] for row in schedule), Decimal('0.00')),
            Decimal('10000.00'),
        )
        self.assertEqual(
            sum((row['interest_amount'] for row in schedule), Decimal('0.00')),
            Decimal('250.00'),
        )

    def test_total_must_equal_principal_plus_interest(self):
        loan = self.make_approved_loan()

        response = self.post_repayment(loan=loan, total='1000.00')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Repayment.objects.count(), 0)
        self.assertEqual(get_available_funds(), Decimal('18000.00'))

    def test_principal_must_be_positive_and_interest_nonnegative(self):
        loan = self.make_approved_loan()
        for principal, interest, total in (
            ('0.00', '100.00', '100.00'),
            ('1000.00', '-1.00', '999.00'),
        ):
            response = self.post_repayment(
                loan=loan,
                principal=principal,
                interest=interest,
                total=total,
            )
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Repayment.objects.count(), 0)

    def test_repayment_must_be_current_scheduled_installment(self):
        loan = self.make_approved_loan()
        future_installment = self.post_repayment(loan=loan, installment_number=2)
        wrong_amount = self.post_repayment(
            loan=loan,
            installment_number=1,
            principal='2000.00',
            interest='100.00',
            total='2100.00',
        )

        self.assertEqual(future_installment.status_code, 400)
        self.assertEqual(wrong_amount.status_code, 400)
        self.assertEqual(Repayment.objects.count(), 0)
        self.assertEqual(get_available_funds(), Decimal('18000.00'))

    def test_only_loan_owner_can_repay(self):
        loan = self.make_approved_loan()
        self.authenticate(self.other_employee)

        response = self.client.post(
            '/api/repayments/',
            {
                'loan_id': str(loan.loan_id),
                'installment_number': 1,
                'principal_amount': '1000.00',
                'interest_amount': '0.00',
                'total_amount': '1000.00',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Repayment.objects.count(), 0)

    def test_pending_rejected_and_completed_loans_cannot_be_repaid(self):
        pending = create_loan(
            employee=self.employee,
            requested_amount=Decimal('10000.00'),
            request_reason='Pending test.',
        )
        response = self.post_repayment(
            loan=pending,
            principal='1000.00',
            interest='0.00',
            total='1000.00',
        )
        self.assertEqual(response.status_code, 400)

        reject_loan(loan=pending, actor=self.admin, reason='Not approved.')
        response = self.post_repayment(
            loan=pending,
            principal='1000.00',
            interest='0.00',
            total='1000.00',
        )
        self.assertEqual(response.status_code, 400)

        completed = Loan.objects.create(
            employee=self.other_employee,
            requested_amount=Decimal('10000.00'),
            request_reason='Completed test.',
            approved_amount=Decimal('10000.00'),
            interest_rate=Decimal('10.00'),
            status=Loan.Status.COMPLETED,
            transaction_id='LOAN-COMPLETED-TEST',
            completed_at=timezone.now(),
            completed_by=self.admin,
        )
        response = self.post_repayment(
            loan=completed,
            principal='1000.00',
            interest='0.00',
            total='1000.00',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Repayment.objects.count(), 0)

    def test_repayment_list_is_limited_to_authenticated_employee(self):
        loan = self.make_approved_loan()
        self.post_repayment(loan=loan)
        other_loan = self.make_approved_loan(employee=self.other_employee)
        self.post_repayment(loan=other_loan)

        self.authenticate(self.employee)
        response = self.client.get('/api/repayments/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['loan_id'], str(loan.loan_id))

    def test_unknown_loan_is_not_found(self):
        self.authenticate()
        response = self.client.post(
            '/api/repayments/',
            {
                'loan_id': '6a1b0ce3-9c2a-4acf-a326-258d46d03210',
                'installment_number': 1,
                'principal_amount': '100.00',
                'interest_amount': '0.00',
                'total_amount': '100.00',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 404)
