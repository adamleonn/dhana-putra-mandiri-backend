from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.models import Customer, Supplier

User = get_user_model()


class Product(models.Model):
    ABC_CHOICES = [
        ('A', 'Class A - High Value (Top 80% Cumulative Value)'),
        ('B', 'Class B - Medium Value (Next 15% Cumulative Value)'),
        ('C', 'Class C - Low Value (Bottom 5% Cumulative Value)'),
    ]

    sku = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default='')

    uom = models.CharField(max_length=32, default='Karton')
    base_unit = models.CharField(max_length=32, default='Liter')
    conversion_factor = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    current_stock = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    moving_average_hpp = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    selling_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    brand = models.CharField(max_length=64, default='Lainnya', db_index=True)
    package_size = models.CharField(max_length=32, default='2L', db_index=True)

    abc_class = models.CharField(max_length=1, choices=ABC_CHOICES, default='B', db_index=True)
    daily_consumption_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    min_stock_level = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.sku} - {self.name} (Stock: {self.current_stock} {self.uom})"

    @property
    def estimated_stock_days(self):
        if self.daily_consumption_rate and self.daily_consumption_rate > Decimal('0.00'):
            return float(self.current_stock / self.daily_consumption_rate)
        return None

    @property
    def is_stock_below_28_days(self):
        days = self.estimated_stock_days
        return days is not None and days < 28.0


class GoodsReceipt(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft (Pending Inspection)'),
        ('confirmed', 'Confirmed (Inventory Updated)'),
        ('discrepancy_detected', 'Discrepancy Detected (Short Delivery / Human Error)'),
        ('cancelled', 'Cancelled'),
    ]

    receipt_number = models.CharField(max_length=64, unique=True, db_index=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='goods_receipts'
    )
    supplier_name = models.CharField(max_length=255, blank=True, default='')
    po_reference = models.CharField(max_length=64, blank=True, default='')
    receipt_date = models.DateField()

    transport_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    unloading_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    notes = models.TextField(blank=True, default='')

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_goods_receipts'
    )
    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='received_shipments'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-receipt_date', '-id']
        verbose_name = 'Goods Receipt'
        verbose_name_plural = 'Goods Receipts'

    def __str__(self):
        name = self.supplier.name if self.supplier else self.supplier_name
        return f"{self.receipt_number} - {name} [{self.status}]"

    @property
    def has_quantity_discrepancy(self):
        return any(item.qty_actual < item.qty_ordered for item in self.items.all())


class GoodsReceiptItem(models.Model):
    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.PROTECT,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='receipt_items'
    )

    qty_ordered = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    qty_actual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    allocated_transport_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    effective_unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.CharField(max_length=255, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Goods Receipt Item'
        verbose_name_plural = 'Goods Receipt Items'

    def __str__(self):
        return f"{self.goods_receipt.receipt_number} - {self.product.sku} (Ordered: {self.qty_ordered}, Actual: {self.qty_actual})"

    @property
    def discrepancy_qty(self):
        diff = self.qty_ordered - self.qty_actual
        return max(Decimal('0.00'), diff)


class Delivery(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft (Preparing Delivery)'),
        ('confirmed', 'Confirmed / Dispatched (Stock Deducted)'),
        ('cancelled', 'Cancelled'),
    ]

    delivery_number = models.CharField(max_length=64, unique=True, db_index=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='deliveries'
    )
    customer_name = models.CharField(max_length=255, blank=True, default='')
    delivery_date = models.DateField()
    driver_name = models.CharField(max_length=128, blank=True, default='')
    vehicle_number = models.CharField(max_length=32, blank=True, default='')
    sales_order_ref = models.CharField(max_length=64, blank=True, default='')

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_deliveries'
    )
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='confirmed_deliveries'
    )
    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-delivery_date', '-id']
        verbose_name = 'Delivery (Surat Jalan)'
        verbose_name_plural = 'Deliveries (Surat Jalan)'

    def __str__(self):
        name = self.customer.name if self.customer else self.customer_name
        return f"{self.delivery_number} -> {name} [{self.status}]"


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.PROTECT,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='delivery_items'
    )
    qty = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    qty_delivered = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    hpp_at_delivery = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Delivery Item'
        verbose_name_plural = 'Delivery Items'

    def __str__(self):
        delivered = self.qty_delivered if self.qty_delivered > Decimal('0.00') else self.qty
        return f"{self.delivery.delivery_number} - {self.product.sku} ({delivered} / {self.qty} {self.product.uom})"

    @property
    def effective_qty(self):
        return self.qty_delivered if self.qty_delivered > Decimal('0.00') else self.qty

    @property
    def total_cogs(self):
        return self.effective_qty * self.hpp_at_delivery


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Masuk'),
        ('OUT', 'Keluar'),
        ('ADJUSTMENT', 'Penyesuaian'),
    ]
    REFERENCE_TYPE_CHOICES = [
        ('GOODS_RECEIPT', 'Penerimaan Barang'),
        ('DELIVERY', 'Surat Jalan / Pengiriman'),
        ('ADJUSTMENT', 'Penyesuaian Stok'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )
    movement_date = models.DateTimeField(default=timezone.now, db_index=True)
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_TYPE_CHOICES, db_index=True)
    reference_type = models.CharField(max_length=32, choices=REFERENCE_TYPE_CHOICES)
    reference_number = models.CharField(max_length=64, db_index=True)
    qty = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    stock_before = models.DecimalField(max_digits=15, decimal_places=2)
    stock_after = models.DecimalField(max_digits=15, decimal_places=2)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date', '-id']
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'

    def __str__(self):
        return f"{self.movement_date.strftime('%Y-%m-%d')} [{self.movement_type}] {self.product.sku} ({self.qty}) - Ref: {self.reference_number}"
