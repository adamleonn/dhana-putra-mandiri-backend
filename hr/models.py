from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

User = get_user_model()


class Employee(models.Model):
    """
    Human Resources Employee Master Data.
    Tracks organizational role, compensation components, and bank details.
    """
    DEPARTMENT_CHOICES = [
        ('direksi', 'Direksi / Executive'),
        ('sales', 'Sales & Marketing'),
        ('gudang', 'Gudang (Warehouse) & Logistics'),
        ('finance', 'Finance (Kasir)'),
        ('accounting', 'Accounting & Pajak'),
        ('general', 'Umum & Operasional'),
    ]

    employee_id = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Unique Employee ID (e.g. EMP-001)"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='employee_profile',
        help_text="Optional linked Django system user for RBAC authorization"
    )
    full_name = models.CharField(max_length=255, db_index=True)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')

    department = models.CharField(max_length=32, choices=DEPARTMENT_CHOICES, db_index=True)
    position = models.CharField(max_length=100)

    # Remuneration components
    base_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Standard monthly basic salary"
    )
    standard_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Fixed recurring monthly allowances (transport, lunch, etc.)"
    )

    # Banking details for disbursements
    bank_name = models.CharField(max_length=64, blank=True, default='')
    bank_account_number = models.CharField(max_length=64, blank=True, default='')
    bank_account_holder = models.CharField(max_length=255, blank=True, default='')

    is_active = models.BooleanField(default=True)
    joined_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

    def __str__(self):
        return f"{self.employee_id} - {self.full_name} ({self.get_department_display()})"


class PayrollSlip(models.Model):
    """
    Monthly employee payroll slip.
    Generation triggers an automatic expense journal posting in the Finance app.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft (Generated)'),
        ('approved', 'Approved by Management'),
        ('paid', 'Paid (Disbursed)'),
    ]

    MONTH_CHOICES = [
        (1, '01 - Januari'),
        (2, '02 - Februari'),
        (3, '03 - Maret'),
        (4, '04 - April'),
        (5, '05 - Mei'),
        (6, '06 - Juni'),
        (7, '07 - Juli'),
        (8, '08 - Agustus'),
        (9, '09 - September'),
        (10, '10 - Oktober'),
        (11, '11 - November'),
        (12, '12 - Desember'),
    ]

    slip_number = models.CharField(max_length=64, unique=True, db_index=True)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='payroll_slips'
    )
    period_month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
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
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Overtime, performance bonus, and allowances"
    )
    deductions = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="BPJS, absences, loan deductions"
    )
    net_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Take-home pay: (base_salary + allowances - deductions)"
    )

    payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft', db_index=True)

    journal_entry = models.ForeignKey(
        'finance.GeneralLedger',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payroll_slips',
        help_text="Automatic expense journal entry posted in finance"
    )
    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_year', '-period_month', '-id']
        verbose_name = 'Payroll Slip'
        verbose_name_plural = 'Payroll Slips'
        unique_together = ('employee', 'period_month', 'period_year')

    def __str__(self):
        return f"{self.slip_number} - {self.employee.full_name} ({self.period_month}/{self.period_year}) - Net: {self.net_salary}"


class EmployeeMutation(models.Model):
    """
    Riwayat mutasi, promosi jabatan, perpindahan departemen, dan penyesuaian gaji karyawan.
    """
    MUTATION_TYPES = [
        ('PROMOTION', 'Promosi Jabatan'),
        ('DEMOTION', 'Demosi Jabatan'),
        ('DEPARTMENT_TRANSFER', 'Mutasi Departemen'),
        ('SALARY_ADJUSTMENT', 'Penyesuaian / Kenaikan Gaji'),
        ('STATUS_CHANGE', 'Perubahan Status Kerja'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='mutations'
    )
    mutation_date = models.DateField()
    mutation_type = models.CharField(max_length=32, choices=MUTATION_TYPES, db_index=True)

    previous_department = models.CharField(max_length=64, blank=True, default='')
    new_department = models.CharField(max_length=64, blank=True, default='')

    previous_position = models.CharField(max_length=100, blank=True, default='')
    new_position = models.CharField(max_length=100, blank=True, default='')

    previous_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Gaji pokok sebelumnya"
    )
    new_salary = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Gaji pokok baru setelah mutasi/penyesuaian"
    )

    reason = models.TextField(help_text="Alasan atau SK mutasi / kenaikan jabatan")
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_mutations'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-mutation_date', '-id']
        verbose_name = 'Mutasi Karyawan'
        verbose_name_plural = 'Daftar Mutasi Karyawan'

    def __str__(self):
        return f"Mutasi {self.employee.full_name} [{self.get_mutation_type_display()}] - {self.mutation_date}"


class LaborRecord(models.Model):
    """
    Catatan Tenaga Kerja (Log harian, absensi/lembur, surat peringatan, penghargaan, insiden gudang).
    """
    RECORD_TYPES = [
        ('ATTENDANCE_NOTE', 'Catatan Kehadiran / Izin'),
        ('OVERTIME_LOG', 'Catatan Lembur'),
        ('INCIDENT', 'Insiden Kerja / Kelalaian Gudang'),
        ('WARNING_LETTER', 'Surat Peringatan (SP)'),
        ('COMMENDATION', 'Apresiasi / Prestasi Kerja'),
        ('GENERAL', 'Catatan Umum Kinerja'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='labor_records'
    )
    record_date = models.DateField(db_index=True)
    record_type = models.CharField(max_length=32, choices=RECORD_TYPES, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()

    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Jumlah jam jika berkaitan dengan lembur atau izin"
    )

    recorded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='recorded_labor_logs'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-record_date', '-id']
        verbose_name = 'Catatan Tenaga Kerja'
        verbose_name_plural = 'Catatan Tenaga Kerja'

    def __str__(self):
        return f"{self.employee.full_name} [{self.get_record_type_display()}] - {self.title}"
