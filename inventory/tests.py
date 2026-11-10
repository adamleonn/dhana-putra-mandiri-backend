from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from finance.models import ChartOfAccounts, GeneralLedger
from .models import Product, GoodsReceipt, GoodsReceiptItem, Delivery, DeliveryItem, StockMovement
from .services import confirm_goods_receipt, confirm_delivery_atomic, calculate_abc_classification

User = get_user_model()


class InventoryBusinessLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        ChartOfAccounts.objects.create(code='1130', name='Piutang Usaha', account_type='ASSET')
        ChartOfAccounts.objects.create(code='1140', name='Persediaan Minyak Goreng', account_type='ASSET')
        ChartOfAccounts.objects.create(code='2110', name='Hutang Usaha', account_type='LIABILITY')
        ChartOfAccounts.objects.create(code='2130', name='Hutang Ongkos Bongkar', account_type='LIABILITY')
        ChartOfAccounts.objects.create(code='4100', name='Pendapatan Penjualan', account_type='REVENUE')
        ChartOfAccounts.objects.create(code='5100', name='HPP Minyak Goreng', account_type='COGS')
        ChartOfAccounts.objects.create(code='6100', name='Beban Bongkar Muat', account_type='EXPENSE')

        self.direktur_group = Group.objects.create(name='Direktur')
        self.gudang_group = Group.objects.create(name='Gudang')
        self.sales_group = Group.objects.create(name='Sales')

        self.direktur = User.objects.create_user(username='pak_direktur', password='password123')
        self.direktur.groups.add(self.direktur_group)

        self.staff_gudang = User.objects.create_user(username='budi_gudang', password='password123')
        self.staff_gudang.groups.add(self.gudang_group)

        self.staff_sales = User.objects.create_user(username='ani_sales', password='password123')
        self.staff_sales.groups.add(self.sales_group)

        self.product = Product.objects.create(
            sku='MNK-BIM-2L-12',
            name='Bimoli Spesial 2L (Dus 6 Pouch)',
            uom='Karton',
            conversion_factor=Decimal('12.00'),
            current_stock=Decimal('100.00'),
            moving_average_hpp=Decimal('200000.00'),
            selling_price=Decimal('230000.00'),
            daily_consumption_rate=Decimal('10.00')
        )

    def test_goods_receipt_hpp_and_cost_allocation(self):
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-202611-001',
            supplier_name='PT Salim Ivomas Pratama',
            receipt_date=timezone.now().date(),
            transport_cost=Decimal('1000000.00'),
            unloading_cost=Decimal('150000.00')
        )
        GoodsReceiptItem.objects.create(
            goods_receipt=receipt,
            product=self.product,
            qty_ordered=Decimal('100.00'),
            qty_actual=Decimal('100.00'),
            purchase_price=Decimal('210000.00')
        )

        confirm_goods_receipt(receipt, self.staff_gudang)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('200.00'))
        self.assertEqual(self.product.moving_average_hpp, Decimal('210000.00'))

        gl = GeneralLedger.objects.get(reference_id='GR-202611-001')
        lines = {l.account.code: (l.debit, l.credit) for l in gl.lines.all()}

        self.assertEqual(lines['1140'][0], Decimal('22000000.00'))
        self.assertEqual(lines['6100'][0], Decimal('150000.00'))

        movement = StockMovement.objects.filter(reference_number='GR-202611-001').first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.movement_type, 'IN')
        self.assertEqual(movement.qty, Decimal('100.00'))
        self.assertEqual(movement.stock_after, Decimal('200.00'))

    def test_goods_receipt_human_error_discrepancy(self):
        receipt = GoodsReceipt.objects.create(
            receipt_number='GR-DISCREPANCY-001',
            supplier_name='PT Musim Mas',
            receipt_date=timezone.now().date()
        )
        GoodsReceiptItem.objects.create(
            goods_receipt=receipt,
            product=self.product,
            qty_ordered=Decimal('100.00'),
            qty_actual=Decimal('90.00'),
            purchase_price=Decimal('200000.00')
        )

        confirm_goods_receipt(receipt, self.staff_gudang)
        receipt.refresh_from_db()
        self.assertEqual(receipt.status, 'discrepancy_detected')
        self.assertTrue(receipt.has_quantity_discrepancy)

    def test_atomic_delivery_confirmation_success(self):
        delivery = Delivery.objects.create(
            delivery_number='DO-202611-001',
            customer_name='Toko Berkah Minyak',
            delivery_date=timezone.now().date()
        )
        DeliveryItem.objects.create(
            delivery=delivery,
            product=self.product,
            qty=Decimal('20.00')
        )

        confirm_delivery_atomic(delivery, self.staff_gudang)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('80.00'))

        item = delivery.items.first()
        self.assertEqual(item.hpp_at_delivery, Decimal('200000.00'))

        gl = GeneralLedger.objects.get(reference_id='DO-202611-001')
        lines = {l.account.code: (l.debit, l.credit) for l in gl.lines.all()}

        self.assertEqual(lines['1130'][0], Decimal('4600000.00'))
        self.assertEqual(lines['4100'][1], Decimal('4600000.00'))
        self.assertEqual(lines['5100'][0], Decimal('4000000.00'))
        self.assertEqual(lines['1140'][1], Decimal('4000000.00'))

        movement = StockMovement.objects.filter(reference_number='DO-202611-001').first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.movement_type, 'OUT')
        self.assertEqual(movement.qty, Decimal('20.00'))
        self.assertEqual(movement.stock_after, Decimal('80.00'))

    def test_atomic_delivery_confirmation_insufficient_stock_rollback(self):
        delivery = Delivery.objects.create(
            delivery_number='DO-EXCEED-001',
            customer_name='Supermarket Rejeki',
            delivery_date=timezone.now().date()
        )
        DeliveryItem.objects.create(
            delivery=delivery,
            product=self.product,
            qty=Decimal('500.00')
        )

        self.client.force_authenticate(user=self.staff_gudang)
        response = self.client.post(f'/api/inventory/deliveries/{delivery.id}/confirm/')

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, Decimal('100.00'))
        self.assertEqual(GeneralLedger.objects.filter(reference_id='DO-EXCEED-001').count(), 0)

    def test_abc_classification_and_stock_runway(self):
        data = calculate_abc_classification()
        self.assertIn('A', data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.estimated_stock_days, 10.0)
        self.assertTrue(self.product.is_stock_below_28_days)
