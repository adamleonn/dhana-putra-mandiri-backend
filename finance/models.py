from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from core.models import Customer, Supplier

User = get_user_model()


class ChartOfAccounts(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('ASSET', 'Asset / Aktiva (Kas, Bank, Piutang, Persediaan)'),
        ('LIABILITY', 'Liability / Kewajiban (Hutang Usaha)'),
        ('EQUITY', 'Equity / Modal'),
        ('REVENUE', 'Revenue / Pendapatan Penjualan'),
        ('COGS', 'Cost of Goods Sold / HPP'),
        ('EXPENSE', 'Expense / Beban Operasional (Bongkar Muat, Gaji, dll.)'),
    ]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=32, choices=ACCOUNT_TYPE_CHOICES, db_index=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Chart of Accounts'
        verbose_name_plural = 'Chart of Accounts'

    def __str__(self):
        return f"{self.code} - {self.name} ({self.get_account_type_display()})"


class AccountingPeriod(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Terbuka'),
        ('SUBMITTED', 'Diajukan'),
        ('CLOSED', 'Ditutup'),
    ]

    period_name = models.CharField(max_length=64, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='OPEN', db_index=True)

    closed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_periods'
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reopened_periods'
    )
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Accounting Period'
        verbose_name_plural = 'Accounting Periods'
        permissions = [
            ('can_manage_accounting_period', 'Can close or reopen accounting periods'),
        ]

    def __str__(self):
        return f"{self.period_name} [{self.status}]"

    @property
    def is_closed(self):
        return self.status == 'CLOSED'

    @property
    def is_open(self):
        return self.status == 'OPEN'


class GeneralLedger(models.Model):
    REFERENCE_TYPE_CHOICES = [
        ('SALES_DELIVERY', 'Surat Jalan / Delivery Dispatched'),
        ('GOODS_RECEIPT', 'Inbound Goods Receipt'),
        ('DEBIT_NOTE', 'Supplier Debit Note'),
        ('PAYMENT', 'Cash / Bank Payment or Receipt'),
        ('PAYROLL', 'Employee Payroll Slip'),
        ('MANUAL', 'Manual Adjustment Journal'),
    ]

    entry_number = models.CharField(max_length=64, unique=True, db_index=True)
    transaction_date = models.DateField(db_index=True)
    period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_entries'
    )
    reference_type = models.CharField(max_length=32, choices=REFERENCE_TYPE_CHOICES)
    reference_id = models.CharField(max_length=64, blank=True, default='')
    description = models.TextField()
    is_posted = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_ledgers'
    )
    posted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='posted_journals'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-id']
        verbose_name = 'General Ledger Entry'
        verbose_name_plural = 'General Ledger Entries'

    def __str__(self):
        return f"{self.entry_number} [{self.reference_type}] - {self.transaction_date}"

    @property
    def total_debit(self):
        return sum((line.debit for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_credit(self):
        return sum((line.credit for line in self.lines.all()), Decimal('0.00'))

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class GeneralLedgerLine(models.Model):
    ledger_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        related_name='lines'
    )
    account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name='ledger_lines'
    )
    debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    memo = models.CharField(max_length=255, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'General Ledger Line'
        verbose_name_plural = 'General Ledger Lines'

    def __str__(self):
        return f"{self.ledger_entry.entry_number} | {self.account.code} | D: {self.debit} C: {self.credit}"


class SalesInvoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid in Full'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=64, unique=True, db_index=True)
    delivery = models.ForeignKey(
        'inventory.Delivery',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sales_invoices'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sales_invoices'
    )
    customer_name = models.CharField(max_length=255, blank=True, default='', db_index=True)
    invoice_date = models.DateField()
    due_date = models.DateField()

    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sales_invoices'
    )
    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-id']
        verbose_name = 'Sales Invoice'
        verbose_name_plural = 'Sales Invoices'

    def __str__(self):
        name = self.customer.name if self.customer else self.customer_name
        return f"{self.invoice_number} - {name} ({self.status}) - Total: {self.total_amount}"

    @property
    def remaining_balance(self):
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)


class SalesInvoiceItem(models.Model):
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.PROTECT,
        related_name='items'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='invoice_lines'
    )
    qty_ordered = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    qty_delivered = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    qty = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    line_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sales Invoice Item'
        verbose_name_plural = 'Sales Invoice Items'

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.sku} ({self.qty} @ {self.unit_price})"


class DebitNote(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ]

    debit_note_number = models.CharField(max_length=64, unique=True, db_index=True)
    goods_receipt = models.ForeignKey(
        'inventory.GoodsReceipt',
        on_delete=models.PROTECT,
        related_name='debit_notes'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='debit_notes'
    )
    supplier_name = models.CharField(max_length=255, blank=True, default='')
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)

    journal_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='debit_notes'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_debit_notes'
    )
    issued_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='issued_debit_notes'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = 'Debit Note (Supplier)'
        verbose_name_plural = 'Debit Notes (Supplier)'

    def __str__(self):
        name = self.supplier.name if self.supplier else self.supplier_name
        return f"{self.debit_note_number} - {name} - Deduct: {self.amount}"


class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Kas Tunai'),
        ('bank_transfer', 'Transfer Bank'),
        ('giro', 'Giro / Cek'),
    ]

    CATEGORY_CHOICES = [
        ('customer_receipt', 'Penerimaan Piutang Customer'),
        ('supplier_payment', 'Pembayaran Hutang Supplier'),
        ('payroll', 'Pembayaran Gaji Pegawai'),
        ('operational_expense', 'Pembayaran Beban Operasional'),
        ('other', 'Lain-lain'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed / Verified'),
        ('cancelled', 'Cancelled'),
    ]

    payment_number = models.CharField(max_length=64, unique=True, db_index=True)
    payment_type = models.CharField(max_length=32, choices=PAYMENT_TYPE_CHOICES)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)

    cash_bank_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='supplier_payments'
    )
    sales_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )
    goods_receipt = models.ForeignKey(
        'inventory.GoodsReceipt',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )
    debit_note = models.ForeignKey(
        DebitNote,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_date = models.DateField(db_index=True)
    reference_number = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True, default='')

    journal_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date', '-id']
        verbose_name = 'Payment (Kas/Bank)'
        verbose_name_plural = 'Payments (Kas/Bank)'

    def __str__(self):
        return f"{self.payment_number} [{self.category}] - {self.payment_date}: {self.amount}"
