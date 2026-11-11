from decimal import Decimal
from datetime import date
from django.test import TransactionTestCase, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Customer, Supplier
from finance.models import ChartOfAccounts, AccountingPeriod, GeneralLedger, GeneralLedgerLine, DebitNote, Payment
from inventory.models import Product, GoodsReceipt, GoodsReceiptItem
from finance.services.journal_service import create_journal_entry
from finance.services.debit_note_service import issue_supplier_debit_note
from finance.services.payment_service import process_supplier_payment
from config.exceptions import PeriodClosedError

User = get_user_model()


class FinanceSecurityAndLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.kas = ChartOfAccounts.objects.create(account_code='1110', name='Kas Kantor', account_type='ASSET', is_cash_bank=True)
        self.bank = ChartOfAccounts.objects.create(account_code='1120', name='BCA', account_type='ASSET', is_cash_bank=True)
        self.ar = ChartOfAccounts.objects.create(account_code='1130', name='Piutang Usaha', account_type='ASSET')
        self.inventory_asset = ChartOfAccounts.objects.create(account_code='1140', name='Persediaan', account_type='ASSET')
        self.ap = ChartOfAccounts.objects.create(account_code='2110', name='Hutang Usaha', account_type='LIABILITY')
        self.revenue = ChartOfAccounts.objects.create(account_code='4100', name='Pendapatan Penjualan', account_type='REVENUE')

        self.today = date(2026, 11, 15)
        self.period = AccountingPeriod.objects.create(
            period_name='2026-11-FIN',
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            status='OPEN'
        )

        self.direktur_group = Group.objects.create(name='Direktur')
        self.accounting_group = Group.objects.create(name='Accounting')
        self.finance_group = Group.objects.create(name='Finance')
        self.gudang_group = Group.objects.create(name='Gudang')
        self.sales_group = Group.objects.create(name='Sales')
        self.stakeholder_group = Group.objects.create(name='Stakeholder')

        self.direktur = User.objects.create_user(username='dir_test', password='password123')
        self.direktur.groups.add(self.direktur_group)

        self.accounting_user = User.objects.create_user(username='acc_test', password='password123')
        self.accounting_user.groups.add(self.accounting_group)

        self.finance_user = User.objects.create_user(username='fin_test', password='password123')
        self.finance_user.groups.add(self.finance_group)

        self.gudang_user = User.objects.create_user(username='gud_test', password='password123')
        self.gudang_user.groups.add(self.gudang_group)

        self.sales_user = User.objects.create_user(username='sal_test', password='password123')
        self.sales_user.groups.add(self.sales_group)

        self.stakeholder_user = User.objects.create_user(username='stk_test', password='password123')
        self.stakeholder_user.groups.add(self.stakeholder_group)

        self.supplier = Supplier.objects.create(code='SUPP-FIN', name='Supplier Finance Test')
        self.product = Product.objects.create(
            sku='PROD-FIN-1',
            name='Produk Finance Test',
            uom='KARTON',
            current_stock=Decimal('100.00'),
            moving_average_hpp=Decimal('150000.00'),
            selling_price=Decimal('180000.00')
        )

    def test_unbalanced_journal_rejected_by_service(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=self.today,
                reference_type='MANUAL',
                reference_id='UNBALANCED_01',
                description='Test Unbalanced',
                lines=[
                    {'account_code': '1110', 'debit': Decimal('1000.00'), 'credit': Decimal('0.00')},
                    {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('800.00')},
                ],
                posted_by=self.accounting_user
            )

    def test_closed_accounting_period_blocks_journal_posting(self):
        self.period.status = 'CLOSED'
        self.period.save()

        with self.assertRaises(PeriodClosedError):
            create_journal_entry(
                transaction_date=self.today,
                reference_type='MANUAL',
                reference_id='CLOSED_01',
                description='Test in Closed Period',
                lines=[
                    {'account_code': '1110', 'debit': Decimal('500.00'), 'credit': Decimal('0.00')},
                    {'account_code': '4100', 'debit': Decimal('0.00'), 'credit': Decimal('500.00')},
                ],
                posted_by=self.accounting_user
            )

    def test_only_direktur_can_close_period_accounting_gets_403(self):
        # 1. Accounting attempts to close period -> 403 Forbidden
        self.client.force_authenticate(user=self.accounting_user)
        res_acc = self.client.post(f"/api/finance/accounting-periods/{self.period.id}/close_period/")
        self.assertEqual(res_acc.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Direktur closes period -> 200 OK
        self.client.force_authenticate(user=self.direktur)
        res_dir = self.client.post(f"/api/finance/accounting-periods/{self.period.id}/close_period/", {'closing_notes': 'Tutup buku resmi'})
        self.assertEqual(res_dir.status_code, status.HTTP_200_OK)
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, 'CLOSED')

    def test_supplier_shortage_blocks_payment_until_debit_note_unblocks(self):
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR/202611/SHORT01',
            supplier=self.supplier,
            receipt_date=self.today,
            payable_amount=Decimal('10000000.00'),
            created_by=self.accounting_user
        )
        GoodsReceiptItem.objects.create(
            goods_receipt=receipt,
            product=self.product,
            qty_ordered=Decimal('100.00'),
            qty_actual=Decimal('80.00'),  # 20 units shortage!
            purchase_price=Decimal('100000.00')
        )

        self.assertTrue(receipt.has_quantity_discrepancy)

        # Attempt supplier payment without debit note -> ValidationError
        with self.assertRaises(ValidationError) as ctx:
            process_supplier_payment(
                goods_receipt=receipt,
                cash_bank_account=self.kas,
                amount=Decimal('8000000.00'),
                payment_date=self.today,
                payment_method='cash',
                actor=self.finance_user
            )
        self.assertIn("PEMBAYARAN DIBLOKIR", str(ctx.exception))

        # Issue Debit Note of 2,000,000 (20 units * 100,000)
        dn = issue_supplier_debit_note(
            goods_receipt=receipt,
            amount=Decimal('2000000.00'),
            reason='Kurang kirim 20 karton',
            issued_by=self.accounting_user,
            issue_date=self.today
        )
        receipt.refresh_from_db()
        self.assertEqual(receipt.debit_note_total, Decimal('2000000.00'))
        self.assertEqual(receipt.net_payable, Decimal('8000000.00'))

        # Payment of net amount 8,000,000 is now unblocked and succeeds!
        payment = process_supplier_payment(
            goods_receipt=receipt,
            cash_bank_account=self.kas,
            amount=Decimal('8000000.00'),
            payment_date=self.today,
            payment_method='cash',
            actor=self.finance_user
        )
        self.assertEqual(payment.status, 'completed')
        receipt.refresh_from_db()
        self.assertEqual(receipt.paid_amount, Decimal('8000000.00'))
        self.assertEqual(receipt.payment_status, 'paid')

    def test_role_field_stripping_and_access_controls(self):
        # 1. Gudang responses must not contain money fields
        self.client.force_authenticate(user=self.gudang_user)
        res_gudang = self.client.get(f"/api/inventory/products/{self.product.id}/")
        self.assertEqual(res_gudang.status_code, status.HTTP_200_OK)
        for field in ['selling_price', 'moving_average_hpp', 'stock_value']:
            self.assertNotIn(field, res_gudang.data, f"Field '{field}' leaked to Gudang role!")

        # 2. Sales responses must not contain HPP
        self.client.force_authenticate(user=self.sales_user)
        res_sales = self.client.get(f"/api/inventory/products/{self.product.id}/")
        self.assertEqual(res_sales.status_code, status.HTTP_200_OK)
        self.assertIn('selling_price', res_sales.data)
        self.assertNotIn('moving_average_hpp', res_sales.data, "moving_average_hpp leaked to Sales role!")

        # 3. Stakeholder POST must be rejected with 403 Forbidden
        self.client.force_authenticate(user=self.stakeholder_user)
        res_stk = self.client.post("/api/core/customers/", {'code': 'CUST-NEW', 'name': 'Hacker'})
        self.assertEqual(res_stk.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Unauthenticated request must return 401 Unauthorized
        self.client.force_authenticate(user=None)
        res_anon = self.client.get("/api/inventory/products/")
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)


class DatabaseTriggerBalanceTests(TransactionTestCase):
    def test_postgresql_trigger_rejects_unbalanced_lines_at_commit(self):
        """
        Verify: Even if an application bug attempts to insert unbalanced lines directly into DB,
        the PostgreSQL deferred constraint trigger aborts the transaction at commit time.
        """
        period = AccountingPeriod.objects.create(
            period_name='2026-11-TRG',
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            status='OPEN'
        )
        user = User.objects.create_user(username='trg_user', password='password123')
        acc_cash = ChartOfAccounts.objects.create(account_code='1110', name='Kas', account_type='ASSET', is_cash_bank=True)
        acc_sales = ChartOfAccounts.objects.create(account_code='4100', name='Sales', account_type='REVENUE')

        with self.assertRaises(Exception) as ctx:
            with transaction.atomic():
                ledger = GeneralLedger.objects.create(
                    transaction_number='JV/202611/TRG01',
                    period=period,
                    date=date(2026, 11, 15),
                    reference_type='TEST_TRG',
                    reference_id='1',
                    description='Unbalanced direct insert',
                    posted_by=user
                )
                GeneralLedgerLine.objects.create(
                    ledger_entry=ledger, account=acc_cash, debit=Decimal('1000.00'), credit=Decimal('0.00')
                )
                GeneralLedgerLine.objects.create(
                    ledger_entry=ledger, account=acc_sales, debit=Decimal('0.00'), credit=Decimal('700.00')  # 300 discrepancy!
                )
        self.assertIn("Database Constraint Violation", str(ctx.exception))
