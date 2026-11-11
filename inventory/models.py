from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from core.models import AuditedModel, Customer, Supplier


class Product(AuditedModel):
    UOM_CHOICES = [
        ('KARTON', 'Karton (Dus)'),
        ('JERIGEN', 'Jerigen'),
        ('POUCH', 'Pouch / Bantal'),
        ('BOTOL', 'Botol'),
    ]

    ABC_CHOICES = [
        ('A', 'Class A (Fast Moving / High Value)'),
        ('B', 'Class B (Medium Value)'),
        ('C', 'Class C (Slow Moving / Low Value)'),
    ]

    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default='')

    uom = models.CharField(
        max_length=32,
        choices=UOM_CHOICES,
        default='KARTON',
        help_text="Unit of Measure transaksi penjualan/pembelian"
    )
    base_unit = models.CharField(
        max_length=16,
        default='LITER',
        help_text="Satuan dasar inventory terkecil (misal: Liter, Kg, Pcs)"
    )
    conversion_factor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Faktor pengali UOM ke base_unit (Contoh: 1 Karton 2L isi 6 = 12.00 Liter)"
    )

    current_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Kuantitas stok fisik di gudang saat ini (dalam satuan UOM)"
    )
    stock_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total nilai rupiah persediaan (stock_value = current_stock * moving_average_hpp)"
    )
    moving_average_hpp = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Harga Pokok Penjualan Moving Average per UOM"
    )
    selling_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Harga jual dasar standar (IDR)"
    )

    brand = models.CharField(max_length=64, blank=True, default='')
    package_size = models.CharField(max_length=64, blank=True, default='', help_text="Contoh: 2 Liter, 1 Liter, 5 Liter")
    lead_time_days = models.PositiveIntegerField(
        default=7,
        help_text="Estimasi waktu tunggu pemesanan ulang dari supplier (hari)"
    )

    abc_class = models.CharField(
        max_length=2,
        choices=ABC_CHOICES,
        default='B',
        db_index=True,
        help_text="Klasifikasi Pareto ABC yang dihitung berkala oleh batch job"
    )
    daily_consumption_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Estimasi konsumsi harian UOM yang dihitung oleh batch job"
    )
    min_stock_level = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Batas minimum stok aman gudang (Safety Stock)"
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['sku']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_stock__gte=Decimal('0.00')),
                name='product_stock_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(stock_value__gte=Decimal('0.00')),
                name='product_stock_value_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(moving_average_hpp__gte=Decimal('0.00')),
                name='product_hpp_non_negative'
            ),
            models.CheckConstraint(
                condition=models.Q(selling_price__gte=Decimal('0.00')),
                name='product_selling_price_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @property
    def estimated_days_of_stock(self):
        if self.daily_consumption_rate > Decimal('0.00'):
            return round(self.current_stock / self.daily_consumption_rate, 1)
        return Decimal('999.0')


class ProductPriceTier(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_tiers'
    )
    min_qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text="Kuantitas minimal order untuk mendapatkan harga tier ini"
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Harga jual per unit pada tier ini"
    )
    effective_from = models.DateField(db_index=True)

    class Meta:
        ordering = ['product', 'min_qty']
        verbose_name = 'Product Price Tier'
        verbose_name_plural = 'Product Price Tiers'
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'min_qty', 'effective_from'],
                name='unique_product_tier_effective'
            )
        ]

    def __str__(self):
        return f"{self.product.sku} >= {self.min_qty}: Rp {self.price:,.2f}"


class PurchaseOrder(AuditedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft PO'),
        ('approved', 'Approved by Management'),
        ('partially_received', 'Partially Received'),
        ('completed', 'Completed (Fully Received)'),
        ('cancelled', 'Cancelled'),
    ]

    po_number = models.CharField(max_length=64, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    order_date = models.DateField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-order_date', '-id']
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name} [{self.status}]"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='po_items'
    )
    qty_ordered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    line_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'
        constraints = [
            models.UniqueConstraint(
                fields=['purchase_order', 'product'],
                name='unique_po_product'
            )
        ]

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.product.sku} ({self.qty_ordered})"

    def save(self, *args, **kwargs):
        self.line_total = (self.qty_ordered * self.unit_price).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class GoodsReceipt(AuditedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft (Barang Sedang Dibongkar)'),
        ('confirmed', 'Confirmed (Stok Masuk & Jurnal Terbit)'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash (Tunai)'),
        ('credit', 'Credit (Termin Hutang Dagang)'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid (Belum Dibayar)'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid (Lunas)'),
    ]

    receipt_number = models.CharField(max_length=64, unique=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='goods_receipts'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='goods_receipts'
    )
    supplier_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    receipt_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=16, choices=PAYMENT_METHOD_CHOICES, default='credit')
    payment_status = models.CharField(max_length=16, choices=PAYMENT_STATUS_CHOICES, default='unpaid', db_index=True)

    transport_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Ongkos kirim masuk yang DIALOKASIKAN ke HPP produk"
    )
    unloading_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Biaya kuli bongkar muat - TIDAK MASUK HPP, langsung dicatat sebagai beban operasional"
    )

    payable_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total hutang supplier (Nilai Barang Aktual + Ongkir Masuk jika ditagihkan)"
    )
    debit_note_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Akumulasi potongan klaim Nota Debit atas kekurangan fisik barang"
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Jumlah pembayaran yang telah diselesaikan ke supplier"
    )

    accounting_period = models.ForeignKey(
        'finance.AccountingPeriod',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='goods_receipts'
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    notes = models.TextField(blank=True, default='')

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='received_shipments'
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='confirmed_goods_receipts'
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-receipt_date', '-id']
        verbose_name = 'Goods Receipt'
        verbose_name_plural = 'Goods Receipts'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(paid_amount__lte=models.F('payable_amount') - models.F('debit_note_total')),
                name='gr_paid_amount_lte_net_payable'
            )
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.supplier.name} [{self.status}]"

    @property
    def net_payable(self):
        return max(Decimal('0.00'), self.payable_amount - self.debit_note_total)

    @property
    def has_quantity_discrepancy(self):
        return any(item.qty_actual < item.qty_ordered for item in self.items.all())


class GoodsReceiptItem(models.Model):
    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='receipt_items'
    )
    qty_ordered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Disalin otomatis dari Purchase Order saat pembuatan BPB"
    )
    qty_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fisik barang aktual yang diterima dan dihitung oleh staf gudang"
    )
    purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    allocated_transport_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Alokasi proporsional ongkir masuk yang menambah nilai kapitalisasi HPP"
    )
    allocated_unloading_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Memo alokasi biaya kuli bongkar (TIDAK BOLEH masuk ke kapitalisasi HPP)"
    )
    effective_unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="HPP efektif satuan masuk = (qty_actual * purchase_price + allocated_transport) / qty_actual"
    )
    line_total = models.DecimalField(
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
        constraints = [
            models.UniqueConstraint(
                fields=['goods_receipt', 'product'],
                name='unique_gr_product'
            ),
            models.CheckConstraint(
                condition=models.Q(qty_actual__gte=Decimal('0.00')),
                name='gr_item_qty_actual_non_negative'
            )
        ]

    def __str__(self):
        return f"{self.goods_receipt.receipt_number} - {self.product.sku} (Order: {self.qty_ordered}, Actual: {self.qty_actual})"

    @property
    def discrepancy_qty(self):
        diff = self.qty_ordered - self.qty_actual
        return max(Decimal('0.00'), diff)


class Delivery(AuditedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft (Persiapan Pengiriman)'),
        ('confirmed', 'Confirmed / Dispatched (Stok Terpotong & Jurnal HPP Terbit)'),
        ('cancelled', 'Cancelled'),
    ]

    delivery_number = models.CharField(max_length=64, unique=True)
    sales_invoice = models.OneToOneField(
        'finance.SalesInvoice',
        on_delete=models.PROTECT,
        related_name='delivery',
        help_text="Alur Invoice-First: Surat Jalan terikat 1:1 pada Sales Invoice"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='deliveries'
    )
    customer_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    delivery_date = models.DateField()
    driver_name = models.CharField(max_length=128, blank=True, default='')
    vehicle_number = models.CharField(max_length=32, blank=True, default='')

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='confirmed_deliveries'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-delivery_date', '-id']
        verbose_name = 'Delivery'
        verbose_name_plural = 'Deliveries'

    def __str__(self):
        return f"{self.delivery_number} - {self.customer.name} [{self.status}]"


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='delivery_items'
    )
    sales_invoice_item = models.ForeignKey(
        'finance.SalesInvoiceItem',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='delivery_items'
    )
    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Kuantitas pesanan yang direncanakan dikirim"
    )
    qty_delivered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Null saat draf; diisi angka aktual saat konfirmasi oleh staf Gudang (bisa 0 jika batal terkirim)"
    )
    hpp_at_delivery = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Snapshot Moving Average HPP saat status surat jalan menjadi confirmed"
    )
    total_cogs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total HPP yang dibukukan = qty_delivered * hpp_at_delivery"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Delivery Item'
        verbose_name_plural = 'Delivery Items'
        constraints = [
            models.UniqueConstraint(
                fields=['delivery', 'sales_invoice_item'],
                name='unique_delivery_sales_invoice_item',
                condition=models.Q(sales_invoice_item__isnull=False)
            )
        ]

    def __str__(self):
        effective = self.effective_qty
        return f"{self.delivery.delivery_number} - {self.product.sku} ({effective} {self.product.uom})"

    @property
    def effective_qty(self):
        """
        Mengatasi Bug Critical: jika qty_delivered adalah 0 (barang tidak terkirim),
        harus mengembalikan 0. Nilai qty rencana hanya digunakan jika qty_delivered masih None (draf).
        """
        if self.qty_delivered is not None:
            return self.qty_delivered
        return self.qty


class StockMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('IN', 'Inbound (Penerimaan BPB)'),
        ('OUT', 'Outbound (Pengiriman Surat Jalan)'),
        ('ADJUSTMENT_IN', 'Penyesuaian Masuk (Opname)'),
        ('ADJUSTMENT_OUT', 'Penyesuaian Keluar (Kerusakan / Kehilangan)'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )
    movement_date = models.DateTimeField(db_index=True)
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_TYPE_CHOICES, db_index=True)
    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Kuantitas mutasi (selalu positif, arah ditentukan oleh movement_type)"
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    stock_before = models.DecimalField(max_digits=12, decimal_places=2)
    stock_after = models.DecimalField(max_digits=12, decimal_places=2)
    hpp_after = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    goods_receipt_item = models.ForeignKey(
        GoodsReceiptItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    delivery_item = models.ForeignKey(
        DeliveryItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='stock_movements'
    )

    reference_type = models.CharField(max_length=32, db_index=True)
    reference_id = models.CharField(max_length=64, db_index=True)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='recorded_stock_movements'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-movement_date', '-id']
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        indexes = [
            models.Index(fields=['product', 'movement_date'], name='idx_movement_prod_date'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reference_type', 'reference_id', 'product'],
                name='unique_stock_movement_ref_prod'
            )
        ]

    def __str__(self):
        return f"[{self.movement_type}] {self.product.sku} ({self.qty}) - Ref: {self.reference_type}#{self.reference_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("StockMovement bersifat append-only dan tidak boleh diubah (UPDATE dilarang).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("StockMovement bersifat append-only dan tidak boleh dihapus (DELETE dilarang).")
