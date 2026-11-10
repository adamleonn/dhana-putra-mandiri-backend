from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from inventory.models import Product, GoodsReceipt, GoodsReceiptItem
from .models import ChartOfAccounts, AccountingPeriod, GeneralLedger, DebitNote, Payment
from .services import (
    create_journal_entry,
    issue_supplier_debit_note,
    validate_supplier_payment_permission
)

User = get_user_model()


class FinanceBusinessLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.kas = ChartOfAccounts.objects.create(code='1110', name='Kas Kantor', account_type='ASSET')
        self.bank = ChartOfAccounts.objects.create(code='1120', name='BCA', account_type='ASSET')
        self.ar = ChartOfAccounts.objects.create(code='1130', name='Piutang Usaha', account_type='ASSET')
        self.inventory_asset = ChartOfAccounts.objects.create(code='1140', name='Persediaan', account_type='ASSET')
        self.ap = ChartOfAccounts.objects.create(code='2110', name='Hutang Usaha', account_type='LIABILITY')
        self.revenue = ChartOfAccounts.objects.create(code='4100', name='Pendapatan Penjualan', account_type='REVENUE')

        self.direktur_group = Group.objects.create(name='Direktur')
        self.accounting_group = Group.objects.create(name='Accounting')
        self.finance_group = Group.objects.create(name='Finance')

        self.direktur = User.objects.create_user(username='pak_direktur', password='password123')
        self.direktur.groups.add(self.direktur_group)

        self.accounting_user = User.objects.create_user(username='siti_accounting', password='password123')
        self.accounting_user.groups.add(self.accounting_group)

        self.finance_user = User.objects.create_user(username='rita_kasir', password='password123')
        self.finance_user.groups.add(self.finance_group)

    def test_unbalanced_journal_rejected(self):
        today = timezone.now().date()
        with self.assertRaises(ValidationError):
            create_journal_entry(
                entry_number='JV-TEST-UNBALANCED',
                transaction_date=today,
                reference_type='MANUAL',
                reference_id='REF-01',
                description='Test Unbalanced',
                lines=[
                    {'account_code': '1110', 'debit': Decimal('1000.00'), 'credit': Decimal('0.00')},
                    {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('800.00')},
                ]
            )

    def test_closed_accounting_period_blocks_journal(self):
        today = timezone.now().date()
        period = AccountingPeriod.objects.create(
            period_name='Current Period',
            start_date=today.replace(day=1),
            end_date=today.replace(day=28),
            status='CLOSED'
        )

        with self.assertRaises(ValidationError):
            create_journal_entry(
                entry_number='JV-CLOSED-PERIOD',
                transaction_date=today,
                reference_type='MANUAL',
                reference_id='REF-CLOSED',
                description='Test Closed Period',
                lines=[
                    {'account_code': '1110', 'debit': Decimal('500.00'), 'credit': Decimal('0.00')},
                    {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('500.00')},
                ]
            )

    def test_direktur_exclusive_period_closing(self):
        today = timezone.now().date()
        period = AccountingPeriod.objects.create(
            period_name='November 2026',
            start_date=today.replace(day=1),
            end_date=today.replace(day=28),
            status='OPEN'
        )

        self.client.force_authenticate(user=self.accounting_user)
        resp = self.client.post(f'/api/finance/accounting-periods/{period.id}/close_period/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.direktur)
        resp = self.client.post(f'/api/finance/accounting-periods/{period.id}/close_period/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        period.refresh_from_db()
        self.assertEqual(period.status, 'CLOSED')
        self.assertTrue(period.is_closed)

        resp_reopen = self.client.post(f'/api/finance/accounting-periods/{period.id}/reopen_period/', {'reason': 'Koreksi jurnal audit'})
        self.assertEqual(resp_reopen.status_code, status.HTTP_200_OK)
        period.refresh_from_db()
        self.assertEqual(period.status, 'OPEN')
        self.assertEqual(period.reopen_reason, 'Koreksi jurnal audit')

    def test_supplier_payment_blocked_on_discrepancy_until_debit_note_issued(self):
        product = Product.objects.create(
            sku='MNK-SAN-1L',
            name='Sania 1L',
            selling_price=Decimal('18000.00')
        )
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-SHORT-001',
            supplier_name='PT Wilmar',
            receipt_date=timezone.now().date(),
            status='discrepancy_detected'
        )
        GoodsReceiptItem.objects.create(
            goods_receipt=receipt,
            product=product,
            qty_ordered=Decimal('100.00'),
            qty_actual=Decimal('80.00'),
            purchase_price=Decimal('15000.00')
        )

        with self.assertRaises(ValidationError):
            validate_supplier_payment_permission(receipt, Decimal('1200000.00'))

        issue_supplier_debit_note(
            goods_receipt=receipt,
            amount=Decimal('300000.00'),
            reason='Barang kurang kirim 20 karton',
            issued_by=self.accounting_user
        )

    def test_balance_sheet_and_reports(self):
        from .reports import generate_balance_sheet, generate_pie_chart_analytics
        sheet = generate_balance_sheet()
        self.assertIn('assets', sheet)
        self.assertIn('liabilities', sheet)
        self.assertIn('equity', sheet)
        self.assertTrue(sheet['summary']['is_balanced'])

        pie_data = generate_pie_chart_analytics()
        self.assertIn('brand_distribution', pie_data)
        self.assertIn('package_size_distribution', pie_data)

    def test_auto_document_numbering(self):
        from config.sequence_generator import generate_document_number
        inv_no = generate_document_number('INV')
        self.assertTrue(inv_no.startswith('INV/'))
        self.assertEqual(len(inv_no.split('/')), 3)

    def test_stakeholder_read_only_access(self):
        stakeholder_group = Group.objects.create(name='Stakeholder')
        stakeholder_user = User.objects.create_user(username='pak_investor', password='password123')
        stakeholder_user.groups.add(stakeholder_group)

        self.client.force_authenticate(user=stakeholder_user)
        resp = self.client.get('/api/finance/reports/balance-sheet/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        resp_post = self.client.post('/api/finance/payments/', {'amount': '100000'})
        self.assertEqual(resp_post.status_code, status.HTTP_403_FORBIDDEN)
