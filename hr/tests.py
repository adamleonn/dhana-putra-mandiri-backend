from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from finance.models import ChartOfAccounts, GeneralLedger
from .models import Employee, PayrollSlip
from .services import generate_employee_payroll, approve_and_disburse_payroll

User = get_user_model()


class HRBusinessLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Seed essential COA
        ChartOfAccounts.objects.create(code='1120', name='BCA', account_type='ASSET')
        ChartOfAccounts.objects.create(code='6200', name='Beban Gaji & Upah', account_type='EXPENSE')

        self.direktur_group = Group.objects.create(name='Direktur')
        self.direktur = User.objects.create_user(username='pak_direktur', password='password123')
        self.direktur.groups.add(self.direktur_group)

        self.employee = Employee.objects.create(
            employee_id='EMP-001',
            full_name='Agus Supriyanto',
            department='gudang',
            position='Kepala Gudang',
            base_salary=Decimal('5000000.00'),
            standard_allowance=Decimal('1000000.00'),
            bank_name='BCA',
            bank_account_number='1234567890',
            bank_account_holder='Agus Supriyanto',
            joined_date=timezone.now().date()
        )

    def test_payroll_generation_and_automatic_expense_journal(self):
        """
        Tests payroll generation and disbursement:
        - Net Salary = Base (5M) + Allowances (1M + 500k overtime) - Deductions (200k) = 6.3M
        - Disbursement triggers automatic expense journal in Finance:
          Debit 6200 (Beban Gaji), Credit 1120 (Bank BCA)
        """
        slip = generate_employee_payroll(
            employee=self.employee,
            period_month=11,
            period_year=2026,
            overtime_allowance=Decimal('500000.00'),
            deductions=Decimal('200000.00')
        )
        self.assertEqual(slip.net_salary, Decimal('6300000.00'))
        self.assertEqual(slip.status, 'draft')

        # Approve and disburse
        approve_and_disburse_payroll(slip, self.direktur, disbursement_account_code='1120')

        slip.refresh_from_db()
        self.assertEqual(slip.status, 'paid')
        self.assertIsNotNone(slip.journal_entry)

        gl = slip.journal_entry
        lines = {l.account.code: (l.debit, l.credit) for l in gl.lines.all()}
        self.assertEqual(lines['6200'][0], Decimal('6300000.00'))  # Beban Gaji Debit
        self.assertEqual(lines['1120'][1], Decimal('6300000.00'))  # Bank BCA Credit

    def test_employee_mutation_and_labor_record(self):
        """Tests recording employee mutations and labor log entries."""
        from .models import EmployeeMutation, LaborRecord
        mutation = EmployeeMutation.objects.create(
            employee=self.employee,
            mutation_date=timezone.now().date(),
            mutation_type='PROMOTION',
            previous_position='Kepala Gudang',
            new_position='Manager Logistik & Distribusi',
            previous_salary=Decimal('5000000.00'),
            new_salary=Decimal('7000000.00'),
            reason='Promosi kinerja tahunan',
            approved_by=self.direktur
        )
        self.assertEqual(mutation.new_salary, Decimal('7000000.00'))

        record = LaborRecord.objects.create(
            employee=self.employee,
            record_date=timezone.now().date(),
            record_type='OVERTIME_LOG',
            title='Lembur Stock Opname Akhir Bulan',
            description='Pelaksanaan stock opname fisik gudang minyak',
            hours=Decimal('4.00'),
            recorded_by=self.direktur
        )
        self.assertEqual(record.hours, Decimal('4.00'))
