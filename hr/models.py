from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from core.models import AuditedModel, TimeStampedModel


class Employee(AuditedModel):
    DEPARTMENT_CHOICES = [
        ('gudang', 'Gudang & Bongkar Muat'),
        ('logistik', 'Logistik & Armada Pengiriman'),
        ('sales', 'Sales & Pemasaran'),
        ('finance', 'Keuangan & Kasir'),
        ('accounting', 'Akuntansi & Perpajakan'),
        ('operasional', 'Administrasi & Operasional'),
        ('manajemen', 'Direksi & Manajemen'),
    ]

    STATUS_CHOICES = [
        ('probation', 'Masa Percobaan (Probation)'),
        ('permanent', 'Karyawan Tetap (PKWTT)'),
        ('contract', 'Karyawan Kontrak (PKWT)'),
        ('internship', 'Magang'),
        ('terminated', 'Berhenti / Diberhentikan'),
    ]

    employee_id = models.CharField(max_length=32, unique=True, help_text="Nomor Induk Karyawan (NIK Internal)")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='employee_profile',
        help_text="Akun login sistem yang terhubung dengan data karyawan ini"
    )
    full_name = models.CharField(max_length=128)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    national_id = models.CharField(max_length=32, blank=True, default='', help_text="Nomor Induk Kependudukan (KTP)")
    tax_id = models.CharField(max_length=64, blank=True, default='', help_text="NPWP Pribadi")

    department = models.CharField(max_length=32, choices=DEPARTMENT_CHOICES, db_index=True)
    position = models.CharField(max_length=64)
    employment_status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='permanent', db_index=True)
    joined_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)

    base_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Gaji pokok bulanan (IDR)"
    )
    standard_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tunjangan tetap bulanan (IDR)"
    )

    bank_name = models.CharField(max_length=64, blank=True, default='')
    bank_account_number = models.CharField(max_length=64, blank=True, default='')
    bank_account_holder = models.CharField(max_length=128, blank=True, default='')

    bpjs_tk_number = models.CharField(max_length=64, blank=True, default='', help_text="Nomor BPJS Ketenagakerjaan")
    bpjs_kes_number = models.CharField(max_length=64, blank=True, default='', help_text="Nomor BPJS Kesehatan")

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['employee_id']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        return f"{self.employee_id} - {self.full_name} ({self.department})"


class PayrollSlip(AuditedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft (Dihitung Sistem)'),
        ('approved', 'Approved by Direktur (Jurnal Akrual Terbit)'),
        ('paid', 'Paid (Kas/Bank Terpotong & Lunas)'),
        ('cancelled', 'Cancelled'),
    ]

    slip_number = models.CharField(max_length=64, unique=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='payroll_slips'
    )
    period_month = models.PositiveSmallIntegerField()
    period_year = models.PositiveSmallIntegerField()

    base_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    allowances = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    deductions = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    net_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)

    accrual_journal_entry = models.ForeignKey(
        'finance.GeneralLedger',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='accrued_payroll_slips',
        help_text="Jurnal pengakuan beban gaji saat slip gaji di-approve: Dr Beban Gaji / Cr Hutang Gaji"
    )
    payment = models.ForeignKey(
        'finance.Payment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payroll_slips',
        help_text="Transaksi pencairan kas/bank saat gaji ditransfer: Dr Hutang Gaji / Cr Kas/Bank"
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_payroll_slips'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='paid_payroll_slips'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-period_year', '-period_month', '-id']
        verbose_name = 'Payroll Slip'
        verbose_name_plural = 'Payroll Slips'
        constraints = [
            models.UniqueConstraint(
                fields=['employee', 'period_month', 'period_year'],
                name='unique_employee_payroll_period'
            ),
            models.CheckConstraint(
                condition=models.Q(net_salary=models.F('base_salary') + models.F('allowances') - models.F('deductions')),
                name='chk_payroll_net_salary_balanced'
            )
        ]

    def __str__(self):
        return f"{self.slip_number} - {self.employee.full_name} ({self.period_month}/{self.period_year}) [Rp {self.net_salary:,.2f}]"


class EmployeeMutation(AuditedModel):
    MUTATION_TYPES = [
        ('promotion', 'Promosi Jabatan'),
        ('demotion', 'Demosi'),
        ('transfer', 'Rotasi Divisi / Departemen'),
        ('salary_adjustment', 'Penyesuaian Gaji Pokok'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='mutations'
    )
    mutation_date = models.DateField()
    effective_date = models.DateField()
    mutation_type = models.CharField(max_length=32, choices=MUTATION_TYPES, db_index=True)

    previous_department = models.CharField(max_length=32, choices=Employee.DEPARTMENT_CHOICES)
    new_department = models.CharField(max_length=32, choices=Employee.DEPARTMENT_CHOICES)

    previous_position = models.CharField(max_length=64)
    new_position = models.CharField(max_length=64)

    previous_salary = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    new_salary = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))

    reason = models.TextField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_mutations'
    )
    is_applied = models.BooleanField(default=False)

    class Meta:
        ordering = ['-mutation_date', '-id']
        verbose_name = 'Employee Mutation'
        verbose_name_plural = 'Employee Mutations'

    def __str__(self):
        return f"Mutasi {self.employee.full_name} ({self.mutation_type}) - TMT: {self.effective_date}"


class LaborRecord(TimeStampedModel):
    RECORD_TYPES = [
        ('ATTENDANCE_NOTE', 'Catatan Kehadiran & Absensi'),
        ('OVERTIME_LOG', 'Log Lembur Bongkar Muat / Armada'),
        ('WARNING_LETTER', 'Surat Peringatan (SP)'),
        ('INCIDENT', 'Catatan Insiden Lapangan / Gudang'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='labor_records'
    )
    record_date = models.DateField(db_index=True)
    record_type = models.CharField(max_length=32, choices=RECORD_TYPES, db_index=True)
    title = models.CharField(max_length=128)
    description = models.TextField()
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Jumlah jam lembur / kerja lapangan"
    )
    hourly_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tarif per jam upah lembur kuli / staf"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recorded_labor_logs'
    )

    class Meta:
        ordering = ['-record_date', '-id']
        verbose_name = 'Labor Record'
        verbose_name_plural = 'Labor Records'

    def __str__(self):
        return f"[{self.record_type}] {self.employee.full_name} ({self.record_date}): {self.title}"
