from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField
from django.conf import settings
from core.models import AuditedModel, TimeStampedModel, Customer, Supplier


class ChartOfAccounts(AuditedModel):
    ACCOUNT_TYPES = [
        ('ASSET', 'Aktiva (Aset)'),
        ('LIABILITY', 'Kewajiban (Hutang)'),
        ('EQUITY', 'Modal (Ekuitas)'),
        ('REVENUE', 'Pendapatan (Penjualan)'),
        ('EXPENSE', 'Beban Operasional & HPP'),
    ]

    REPORT_GROUPS = [
        ('CURRENT_ASSET', 'Aset Lancar (Kas, Bank, Piutang, Persediaan)'),
        ('FIXED_ASSET', 'Aset Tetap (Kendaraan, Bangunan)'),
        ('CURRENT_LIABILITY', 'Kewajiban Lancar (Hutang Dagang, Beban Akrual)'),
        ('LONG_TERM_LIABILITY', 'Kewajiban Jangka Panjang'),
        ('EQUITY', 'Ekuitas Pemilik'),
        ('SALES', 'Pendapatan Penjualan'),
        ('COGS', 'Harga Pokok Penjualan (HPP)'),
        ('LABOR_EXPENSE', 'Beban Upah & Tenaga Kerja Gudang'),
        ('TRANSPORT_EXPENSE', 'Beban Transportasi & Logistik'),
        ('ADMIN_EXPENSE', 'Beban Umum & Administrasi'),
        ('OTHER_EXPENSE', 'Beban / Pendapatan Lain-lain'),
        ('TAX_EXPENSE', 'Beban Pajak'),
    ]

    BALANCE_CHOICES = [
        ('D', 'Debit'),
        ('C', 'Credit'),
    ]

    account_code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    account_type = models.CharField(max_length=16, choices=ACCOUNT_TYPES, db_index=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )
    report_group = models.CharField(max_length=32, choices=REPORT_GROUPS, default='CURRENT_ASSET')
    normal_balance = models.CharField(max_length=1, choices=BALANCE_CHOICES, default='D')
    is_cash_bank = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Centang jika akun ini adalah Kas Tunai atau Rekening Bank"
    )
    is_postable = models.BooleanField(
        default=True,
        help_text="Hanya akun postable (detail) yang dapat dipilih dalam baris jurnal"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['account_code']
        verbose_name = 'Chart of Accounts'
        verbose_name_plural = 'Charts of Accounts'

    def __str__(self):
        return f"{self.account_code} - {self.name}"


class AccountingPeriod(AuditedModel):
    STATUS_CHOICES = [
        ('OPEN', 'Open (Periode Aktif)'),
        ('SUBMITTED', 'Submitted (Pengajuan Tutup Buku oleh Accounting)'),
        ('CLOSED', 'Closed (Ditutup Permanen oleh Direktur)'),
    ]

    period_name = models.CharField(max_length=32, unique=True, help_text="Contoh: 2026-11 (November 2026)")
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='OPEN', db_index=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='submitted_periods'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='closed_periods'
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reopened_periods'
    )
    reopened_at = models.DateTimeField(null=True, blank=True)
    reopen_reason = models.TextField(blank=True, default='')
    closing_notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Accounting Period'
        verbose_name_plural = 'Accounting Periods'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='period_end_date_gte_start_date'
            ),
            ExclusionConstraint(
                name='exclude_overlapping_accounting_periods',
                expressions=[
                    (
                        models.Func(
                            models.F('start_date'),
                            models.F('end_date'),
                            models.Value('[]'),
                            function='daterange',
                            output_field=DateRangeField(),
                        ),
                        '&&',
                    )
                ],
            ),
        ]

    def __str__(self):
        return f"{self.period_name} [{self.status}]"

    @property
    def is_closed(self) -> bool:
        return self.status == 'CLOSED'


class GeneralLedger(TimeStampedModel):
    transaction_number = models.CharField(max_length=64, unique=True)
    period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name='ledger_entries'
    )
    date = models.DateField(db_index=True)
    reference_type = models.CharField(max_length=32, db_index=True)
    reference_id = models.CharField(max_length=64, db_index=True)
    description = models.TextField(blank=True, default='')
    is_posted = models.BooleanField(default=True, db_index=True)
    reversal_of = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reversals'
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='posted_journals'
    )

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = 'General Ledger'
        verbose_name_plural = 'General Ledgers'
        constraints = [
            models.UniqueConstraint(
                fields=['reference_type', 'reference_id'],
                name='unique_ledger_reference',
                condition=models.Q(reversal_of__isnull=True)
            )
        ]

    def __str__(self):
        return f"{self.transaction_number} ({self.date}) - {self.reference_type}#{self.reference_id}"

    def save(self, *args, **kwargs):
        if self.pk and self.is_posted:
            existing = GeneralLedger.objects.filter(pk=self.pk).values('is_posted').first()
            if existing and existing['is_posted']:
                raise ValidationError("Jurnal yang sudah diposting bersifat immutable (UPDATE dilarang, gunakan entri pembalik/reversal).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_posted:
            raise ValidationError("Jurnal yang sudah diposting dilarang dihapus (DELETE dilarang, gunakan entri pembalik/reversal).")
        super().delete(*args, **kwargs)


class GeneralLedgerLine(models.Model):
    ledger_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.CASCADE,
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
        indexes = [
            models.Index(fields=['account', 'ledger_entry'], name='idx_line_acc_entry'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(debit__gt=Decimal('0.00')) & models.Q(credit=Decimal('0.00'))) |
                    (models.Q(debit=Decimal('0.00')) & models.Q(credit__gt=Decimal('0.00')))
                ),
                name='chk_line_strictly_debit_or_credit'
            )
        ]

    def __str__(self):
        return f"{self.ledger_entry.transaction_number} - {self.account.account_code}: D={self.debit} C={self.credit}"


class SalesInvoice(AuditedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft Faktur (Dibuat Sales)'),
        ('approved', 'Approved (Siap Kirim / Dispatched)'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Fully Paid (Lunas)'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash (Tunai)'),
        ('credit', 'Credit (Termin Piutang)'),
    ]

    invoice_number = models.CharField(max_length=64, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='sales_invoices'
    )
    customer_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    invoice_date = models.DateField(db_index=True)
    due_date = models.DateField(db_index=True)
    payment_method = models.CharField(max_length=16, choices=PAYMENT_METHOD_CHOICES, default='credit')

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
    journal_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sales_invoices'
    )
    revision_no = models.PositiveIntegerField(default=0, help_text="Nomor revisi jika ada kekurangan fisik barang kirim")
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-invoice_date', '-id']
        verbose_name = 'Sales Invoice'
        verbose_name_plural = 'Sales Invoices'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F('invoice_date')),
                name='invoice_due_date_gte_invoice_date'
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount=models.F('subtotal') - models.F('discount_amount')),
                name='invoice_total_amount_equals_subtotal_minus_discount'
            ),
            models.CheckConstraint(
                condition=models.Q(paid_amount__gte=Decimal('0.00')) & models.Q(paid_amount__lte=models.F('total_amount')),
                name='invoice_paid_amount_range'
            )
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name} [Rp {self.total_amount:,.2f}]"

    @property
    def remaining_due(self):
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)


class SalesInvoiceItem(models.Model):
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='invoice_lines'
    )
    qty_ordered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Kuantitas yang dipesan pelanggan pada draf invoice"
    )
    qty_delivered = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Kuantitas fisik aktual yang dikonfirmasi terkirim oleh Gudang"
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
        constraints = [
            models.UniqueConstraint(
                fields=['invoice', 'product'],
                name='unique_invoice_product'
            )
        ]

    def __str__(self):
        effective = self.effective_billed_qty
        return f"{self.invoice.invoice_number} - {self.product.sku} ({effective} @ {self.unit_price})"

    @property
    def effective_billed_qty(self):
        if self.qty_delivered is not None:
            return self.qty_delivered
        return self.qty_ordered


class SalesInvoiceRevision(models.Model):
    invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name='revisions'
    )
    revised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='invoice_revisions'
    )
    revision_number = models.PositiveIntegerField()
    old_total = models.DecimalField(max_digits=15, decimal_places=2)
    new_total = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sales Invoice Revision'
        verbose_name_plural = 'Sales Invoice Revisions'

    def __str__(self):
        return f"{self.invoice.invoice_number} Rev#{self.revision_number}: {self.old_total} -> {self.new_total}"


class DebitNote(AuditedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft (Diajukan Accounting)'),
        ('approved', 'Approved by Direktur'),
        ('applied', 'Applied (Potong Hutang Supplier Selesai)'),
        ('cancelled', 'Cancelled'),
    ]

    debit_note_number = models.CharField(max_length=64, unique=True)
    goods_receipt = models.ForeignKey(
        'inventory.GoodsReceipt',
        on_delete=models.PROTECT,
        related_name='debit_notes'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='debit_notes'
    )
    supplier_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    date = models.DateField(db_index=True)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Nominal potongan klaim kekurangan barang = shortage_qty * purchase_price"
    )
    reason = models.TextField(help_text="Alasan klaim kekurangan / kerusakan fisik barang")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)

    journal_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='debit_notes'
    )
    period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name='debit_notes'
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='issued_debit_notes'
    )

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = 'Debit Note'
        verbose_name_plural = 'Debit Notes'

    def __str__(self):
        return f"{self.debit_note_number} - {self.supplier.name} (Rp {self.amount:,.2f}) [{self.status}]"


class Payment(AuditedModel):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash (Tunai)'),
        ('bank_transfer', 'Bank Transfer'),
        ('giro', 'Bilyet Giro / Cek'),
    ]

    CATEGORY_CHOICES = [
        ('customer_receipt', 'Penerimaan Pelunasan Piutang Pelanggan (BKM)'),
        ('supplier_payment', 'Pembayaran Hutang Dagang Supplier (BKK)'),
        ('payroll', 'Pencairan Gaji Karyawan (Payroll BKK)'),
        ('operational_expense', 'Pengeluaran Beban Operasional'),
        ('other', 'Lain-lain'),
    ]

    DIRECTION_CHOICES = [
        ('IN', 'Kas Masuk (Inbound / BKM)'),
        ('OUT', 'Kas Keluar (Outbound / BKK)'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft Pembayaran'),
        ('completed', 'Completed (Kas/Bank Berkurang & Jurnal Terbit)'),
        ('cancelled', 'Cancelled (Void / Jurnal Pembalik Terbit)'),
    ]

    payment_number = models.CharField(max_length=64, unique=True)
    payment_method = models.CharField(max_length=32, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)
    direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES, default='IN', db_index=True)

    cash_bank_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.PROTECT,
        related_name='payments',
        limit_choices_to={'is_cash_bank': True},
        help_text="Rekening Kas atau Bank yang digunakan untuk mutasi kas"
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
    payroll_slip = models.ForeignKey(
        'hr.PayrollSlip',
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
    reference_number = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)
    notes = models.TextField(blank=True, default='')

    journal_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )
    reversal_journal_entry = models.ForeignKey(
        GeneralLedger,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reversed_payments'
    )

    class Meta:
        ordering = ['-payment_date', '-id']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"{self.payment_number} [{self.direction}] - Rp {self.amount:,.2f} ({self.category})"
