from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from finance.models import ChartOfAccounts, AccountingPeriod, GeneralLedger
from hr.models import Employee, PayrollSlip, EmployeeMutation
from hr.services.payroll_service import (
    generate_employee_payroll,
    approve_payroll_slip,
    apply_employee_mutation
)
from finance.services.payment_service import process_payroll_payment

User = get_user_model()


class HRBusinessLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Seed essential COA
        self.bank = ChartOfAccounts.objects.create(account_code='1120', name='BCA', account_type='ASSET', is_cash_bank=True)
        self.salary_payable = ChartOfAccounts.objects.create(account_code='2120', name='Hutang Gaji', account_type='LIABILITY')
        self.salary_expense = ChartOfAccounts.objects.create(account_code='6110', name='Beban Gaji', account_type='EXPENSE')

        self.today = date(2026, 11, 15)
        self.period = AccountingPeriod.objects.create(
            period_name='2026-11-HR',
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            status='OPEN'
        )

        self.direktur_group = Group.objects.create(name='Direktur')
        self.sales_group = Group.objects.create(name='Sales')

        self.direktur = User.objects.create_user(username='dir_hr', password='password123')
        self.direktur.groups.add(self.direktur_group)

        self.sales_user = User.objects.create_user(username='sales_hr', password='password123')
        self.sales_user.groups.add(self.sales_group)

        self.employee = Employee.objects.create(
            employee_id='EMP-HR-001',
            full_name='Agus Supriyanto',
            department='gudang',
            position='Kepala Gudang',
            base_salary=Decimal('5000000.00'),
            standard_allowance=Decimal('1000000.00'),
            bank_name='BCA',
            bank_account_number='1234567890',
            bank_account_holder='Agus Supriyanto',
            joined_date=self.today
        )

    def test_two_stage_payroll_accounting_lifecycle(self):
        """
        Stage 1: Generate draft slip -> Net Salary = 5M + 1M + 500k overtime - 200k = 6.3M.
        Stage 2: Approve by Direktur -> Accrual Journal (Dr 6110 Beban Gaji / Cr 2120 Hutang Gaji).
        Stage 3: Disburse via Payment -> Cash Journal (Dr 2120 Hutang Gaji / Cr 1120 Bank BCA).
        """
        slip = generate_employee_payroll(
            employee=self.employee,
            period_month=11,
            period_year=2026,
            overtime_allowance=Decimal('500000.00'),
            deductions=Decimal('200000.00'),
            actor=self.direktur
        )
        self.assertEqual(slip.net_salary, Decimal('6300000.00'))
        self.assertEqual(slip.status, 'draft')

        # Approve by Direktur
        approved_slip = approve_payroll_slip(slip, self.direktur)
        self.assertEqual(approved_slip.status, 'approved')
        self.assertIsNotNone(approved_slip.accrual_journal_entry)
        self.assertEqual(approved_slip.accrual_journal_entry.reference_type, 'PAYROLL_ACCRUAL')

        # Disburse by Kasir / Finance
        payment = process_payroll_payment(
            payroll_slip=approved_slip,
            cash_bank_account=self.bank,
            payment_date=self.today,
            payment_method='bank_transfer',
            actor=self.direktur
        )
        approved_slip.refresh_from_db()
        self.assertEqual(approved_slip.status, 'paid')
        self.assertEqual(payment.amount, Decimal('6300000.00'))

    def test_employee_sensitive_fields_masked_for_non_direktur(self):
        self.client.force_authenticate(user=self.sales_user)
        res = self.client.get(f"/api/hr/employees/{self.employee.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertNotIn('base_salary', res.data)
        self.assertNotIn('standard_allowance', res.data)
        self.assertNotIn('bank_account_number', res.data)

        # Direktur sees everything
        self.client.force_authenticate(user=self.direktur)
        res_dir = self.client.get(f"/api/hr/employees/{self.employee.id}/")
        self.assertEqual(res_dir.status_code, status.HTTP_200_OK)
        self.assertIn('base_salary', res_dir.data)
        self.assertIn('bank_account_number', res_dir.data)

    def test_employee_mutation_applied_atomically(self):
        mutation = EmployeeMutation.objects.create(
            employee=self.employee,
            mutation_date=self.today,
            effective_date=self.today,
            mutation_type='promotion',
            new_department='logistik',
            new_position='Manager Logistik',
            new_salary=Decimal('7500000.00'),
            reason='Promosi prestasi'
        )
        applied = apply_employee_mutation(mutation, self.direktur)

        self.assertTrue(applied.is_applied)
        self.assertEqual(applied.previous_department, 'gudang')
        self.assertEqual(applied.previous_salary, Decimal('5000000.00'))

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.department, 'logistik')
        self.assertEqual(self.employee.position, 'Manager Logistik')
        self.assertEqual(self.employee.base_salary, Decimal('7500000.00'))
