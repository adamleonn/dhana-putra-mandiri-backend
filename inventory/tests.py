import threading
from decimal import Decimal
from datetime import date
from django.test import TransactionTestCase, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from core.models import Customer, Supplier
from finance.models import ChartOfAccounts, AccountingPeriod, SalesInvoice, SalesInvoiceItem
from inventory.models import Product, GoodsReceipt, GoodsReceiptItem, Delivery, DeliveryItem, StockMovement
from inventory.services.hpp_service import confirm_goods_receipt
from inventory.services.delivery_service import confirm_delivery_atomic
from config.exceptions import InsufficientStockError

User = get_user_model()


class InventoryBusinessLogicTests(TestCase):
    def setUp(self):
        # Create standard COA accounts
        ChartOfAccounts.objects.create(account_code='1110', name='Kas Tunai', account_type='ASSET', is_cash_bank=True)
        ChartOfAccounts.objects.create(account_code='1130', name='Piutang Usaha', account_type='ASSET')
        ChartOfAccounts.objects.create(account_code='1140', name='Persediaan Minyak', account_type='ASSET')
        ChartOfAccounts.objects.create(account_code='2110', name='Hutang Dagang', account_type='LIABILITY')
        ChartOfAccounts.objects.create(account_code='4100', name='Penjualan', account_type='REVENUE')
        ChartOfAccounts.objects.create(account_code='5100', name='HPP Minyak', account_type='EXPENSE')
        ChartOfAccounts.objects.create(account_code='6120', name='Beban Bongkar Muat', account_type='EXPENSE')

        self.today = date(2026, 11, 10)
        self.period = AccountingPeriod.objects.create(
            period_name='2026-11',
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            status='OPEN'
        )

        self.user_gudang = User.objects.create_user(username='gudang_tester', password='password123')
        self.user_sales = User.objects.create_user(username='sales_tester', password='password123')

        self.customer = Customer.objects.create(code='CUST-TEST', name='Customer Test', credit_limit=Decimal('10000000.00'))
        self.supplier = Supplier.objects.create(code='SUPP-TEST', name='Supplier Test')

        self.product = Product.objects.create(
            sku='TEST-BIM-2L',
            name='Bimoli 2L Test',
            uom='KARTON',
            current_stock=Decimal('0.00'),
            stock_value=Decimal('0.00'),
            moving_average_hpp=Decimal('0.00'),
            selling_price=Decimal('220000.00')
        )

    def test_moving_average_with_transport_allocation(self):
        """
        Verify: 100 units @ 170,000 + transport 800,000 => HPP 178,000.
        Unloading cost 200,000 must NEVER enter HPP.
        """
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR/202611/9901',
            supplier=self.supplier,
            receipt_date=self.today,
            transport_cost=Decimal('800000.00'),
            unloading_cost=Decimal('200000.00'),
            created_by=self.user_gudang
        )
        item = GoodsReceiptItem.objects.create(
            goods_receipt=receipt,
            product=self.product,
            qty_ordered=Decimal('100.00'),
            qty_actual=Decimal('100.00'),
            purchase_price=Decimal('170000.00')
        )

        confirm_goods_receipt(receipt, self.user_gudang)

        self.product.refresh_from_db()
        item.refresh_from_db()

        # Item checks
        self.assertEqual(item.allocated_transport_cost, Decimal('800000.00'))
        self.assertEqual(item.effective_unit_cost, Decimal('178000.00'))

        # Product checks
        self.assertEqual(self.product.current_stock, Decimal('100.00'))
        self.assertEqual(self.product.stock_value, Decimal('17800000.00'))
        self.assertEqual(self.product.moving_average_hpp, Decimal('178000.00'))

        # StockMovement check
        movement = StockMovement.objects.get(reference_type='GOODS_RECEIPT', reference_id=str(receipt.id))
        self.assertEqual(movement.movement_type, 'IN')
        self.assertEqual(movement.qty, Decimal('100.00'))
        self.assertEqual(movement.unit_cost, Decimal('178000.00'))
        self.assertEqual(movement.total_cost, Decimal('17800000.00'))

    def test_zero_delivered_line_costed_as_zero_and_effective_qty_bug(self):
        """
        Critical regression test: Line with qty_delivered = 0 must be costed as 0 and not billed.
        """
        self.product.current_stock = Decimal('50.00')
        self.product.stock_value = Decimal('10000000.00')
        self.product.moving_average_hpp = Decimal('200000.00')
        self.product.save()

        inv = SalesInvoice.objects.create(
            invoice_number='INV/202611/9901',
            customer=self.customer,
            invoice_date=self.today,
            due_date=self.today,
            subtotal=Decimal('2200000.00'),
            total_amount=Decimal('2200000.00'),
            status='draft',
            created_by=self.user_sales
        )
        inv_item = SalesInvoiceItem.objects.create(
            invoice=inv,
            product=self.product,
            qty_ordered=Decimal('10.00'),
            unit_price=Decimal('220000.00'),
            line_total=Decimal('2200000.00')
        )

        delivery = Delivery.objects.create(
            delivery_number='SJ/202611/9901',
            sales_invoice=inv,
            customer=self.customer,
            delivery_date=self.today,
            created_by=self.user_sales
        )
        del_item = DeliveryItem.objects.create(
            delivery=delivery,
            product=self.product,
            sales_invoice_item=inv_item,
            qty=Decimal('10.00'),
            qty_delivered=Decimal('0.00')  # Genuinely not delivered!
        )

        # Before confirmation, effective_qty is 0
        self.assertEqual(del_item.effective_qty, Decimal('0.00'))

        confirm_delivery_atomic(delivery, self.user_gudang)

        del_item.refresh_from_db()
        inv_item.refresh_from_db()
        inv.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(del_item.hpp_at_delivery, Decimal('0.00'))
        self.assertEqual(del_item.total_cogs, Decimal('0.00'))
        self.assertEqual(inv_item.qty_delivered, Decimal('0.00'))
        self.assertEqual(inv_item.line_total, Decimal('0.00'))
        self.assertEqual(inv.total_amount, Decimal('0.00'))
        self.assertEqual(self.product.current_stock, Decimal('50.00'))

    def test_double_confirm_is_strictly_rejected(self):
        """
        Verify that confirming a delivery twice is rejected with ValidationError.
        """
        self.product.current_stock = Decimal('50.00')
        self.product.stock_value = Decimal('10000000.00')
        self.product.moving_average_hpp = Decimal('200000.00')
        self.product.save()

        inv = SalesInvoice.objects.create(
            invoice_number='INV/202611/9902',
            customer=self.customer,
            invoice_date=self.today,
            due_date=self.today,
            subtotal=Decimal('1100000.00'),
            total_amount=Decimal('1100000.00'),
            status='draft',
            created_by=self.user_sales
        )
        inv_item = SalesInvoiceItem.objects.create(
            invoice=inv,
            product=self.product,
            qty_ordered=Decimal('5.00'),
            unit_price=Decimal('220000.00'),
            line_total=Decimal('1100000.00')
        )
        delivery = Delivery.objects.create(
            delivery_number='SJ/202611/9902',
            sales_invoice=inv,
            customer=self.customer,
            delivery_date=self.today,
            created_by=self.user_sales
        )
        DeliveryItem.objects.create(
            delivery=delivery,
            product=self.product,
            sales_invoice_item=inv_item,
            qty=Decimal('5.00'),
            qty_delivered=Decimal('5.00')
        )

        confirm_delivery_atomic(delivery, self.user_gudang)
        self.assertEqual(delivery.status, 'confirmed')

        with self.assertRaises(ValidationError):
            confirm_delivery_atomic(delivery, self.user_gudang)


class DeliveryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        ChartOfAccounts.objects.create(account_code='1130', name='Piutang Usaha', account_type='ASSET')
        ChartOfAccounts.objects.create(account_code='1140', name='Persediaan Minyak', account_type='ASSET')
        ChartOfAccounts.objects.create(account_code='4100', name='Penjualan', account_type='REVENUE')
        ChartOfAccounts.objects.create(account_code='5100', name='HPP Minyak', account_type='EXPENSE')

        self.today = date(2026, 11, 10)
        AccountingPeriod.objects.create(
            period_name='2026-11-CONC',
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            status='OPEN'
        )

        self.user_gudang = User.objects.create_user(username='gudang_conc', password='password123')
        self.user_sales = User.objects.create_user(username='sales_conc', password='password123')

        self.customer = Customer.objects.create(code='CUST-CONC', name='Customer Concurrency')
        self.product = Product.objects.create(
            sku='CONC-BIM-2L',
            name='Bimoli Concurrency Test',
            uom='KARTON',
            current_stock=Decimal('5.00'),
            stock_value=Decimal('1000000.00'),
            moving_average_hpp=Decimal('200000.00'),
            selling_price=Decimal('240000.00')
        )

    def test_two_concurrent_confirmations_competing_for_stock(self):
        """
        Verify: Two concurrent deliveries competing for 5 units (4 + 4):
        Exactly one must succeed, the other must fail with InsufficientStockError,
        and final stock must be exactly 1.
        """
        # Create Delivery A (4 units)
        inv_a = SalesInvoice.objects.create(
            invoice_number='INV/202611/A001',
            customer=self.customer,
            invoice_date=self.today,
            due_date=self.today,
            subtotal=Decimal('960000.00'),
            total_amount=Decimal('960000.00'),
            created_by=self.user_sales
        )
        item_a = SalesInvoiceItem.objects.create(
            invoice=inv_a, product=self.product, qty_ordered=Decimal('4.00'), unit_price=Decimal('240000.00'), line_total=Decimal('960000.00')
        )
        del_a = Delivery.objects.create(
            delivery_number='SJ/202611/A001', sales_invoice=inv_a, customer=self.customer, delivery_date=self.today, created_by=self.user_sales
        )
        DeliveryItem.objects.create(delivery=del_a, product=self.product, sales_invoice_item=item_a, qty=Decimal('4.00'), qty_delivered=Decimal('4.00'))

        # Create Delivery B (4 units)
        inv_b = SalesInvoice.objects.create(
            invoice_number='INV/202611/B001',
            customer=self.customer,
            invoice_date=self.today,
            due_date=self.today,
            subtotal=Decimal('960000.00'),
            total_amount=Decimal('960000.00'),
            created_by=self.user_sales
        )
        item_b = SalesInvoiceItem.objects.create(
            invoice=inv_b, product=self.product, qty_ordered=Decimal('4.00'), unit_price=Decimal('240000.00'), line_total=Decimal('960000.00')
        )
        del_b = Delivery.objects.create(
            delivery_number='SJ/202611/B001', sales_invoice=inv_b, customer=self.customer, delivery_date=self.today, created_by=self.user_sales
        )
        DeliveryItem.objects.create(delivery=del_b, product=self.product, sales_invoice_item=item_b, qty=Decimal('4.00'), qty_delivered=Decimal('4.00'))

        results = []
        errors = []

        def run_confirm(deliv):
            try:
                res = confirm_delivery_atomic(deliv, self.user_gudang)
                results.append(res)
            except Exception as e:
                errors.append(e)
            finally:
                from django.db import connections
                for conn in connections.all(initialized_only=True):
                    conn.close()

        t1 = threading.Thread(target=run_confirm, args=(del_a,))
        t2 = threading.Thread(target=run_confirm, args=(del_b,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 1, "Expected exactly 1 successful confirmation!")
        self.assertEqual(len(errors), 1, "Expected exactly 1 failed confirmation due to stock!")
        self.assertIsInstance(errors[0], InsufficientStockError)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('1.00'), "Final stock must be exactly 1 unit (5 - 4)!")
