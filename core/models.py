from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.conf import settings


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        help_text="User yang membuat dokumen transaksi ini"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        help_text="User terakhir yang memperbarui dokumen ini"
    )

    class Meta:
        abstract = True


class User(AbstractUser):
    oidc_issuer = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="OIDC Issuer URL (Identity Provider)"
    )
    oidc_subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="OIDC Subject Identifier (sub)"
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        constraints = [
            models.UniqueConstraint(
                fields=['oidc_issuer', 'oidc_subject'],
                name='unique_oidc_identity',
                condition=models.Q(oidc_issuer__isnull=False, oidc_subject__isnull=False)
            )
        ]

    def __str__(self):
        return self.username


class DocumentSequenceCounter(models.Model):
    doc_type = models.CharField(max_length=32, db_index=True)
    period_key = models.CharField(max_length=16, db_index=True)
    last_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document Sequence Counter"
        verbose_name_plural = "Document Sequence Counters"
        constraints = [
            models.UniqueConstraint(
                fields=['doc_type', 'period_key'],
                name='unique_doc_type_period_key'
            )
        ]

    def __str__(self):
        return f"{self.doc_type}-{self.period_key}: {self.last_number}"


class Customer(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    tax_id = models.CharField(max_length=64, blank=True, default='', help_text="NPWP Pelanggan")
    contact_person = models.CharField(max_length=128, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Batas plafon kredit piutang (IDR)"
    )
    payment_term_days = models.PositiveIntegerField(
        default=0,
        help_text="Termin jatuh tempo pembayaran dalam hari (TOP)"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['code']
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(credit_limit__gte=Decimal('0.00')),
                name='customer_credit_limit_non_negative'
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Supplier(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    tax_id = models.CharField(max_length=64, blank=True, default='', help_text="NPWP Supplier")
    contact_person = models.CharField(max_length=128, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    payment_term_days = models.PositiveIntegerField(
        default=0,
        help_text="Termin pembayaran hutang dagang dalam hari"
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['code']
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return f"{self.code} - {self.name}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('CONFIRM', 'Confirm'),
        ('CANCEL', 'Cancel'),
        ('APPROVE', 'Approve'),
        ('CLOSE_PERIOD', 'Close Accounting Period'),
        ('REOPEN_PERIOD', 'Reopen Accounting Period'),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="Pengguna yang melakukan aksi"
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=128, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True, default='')
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        actor_name = self.actor.username if self.actor else 'system'
        return f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {actor_name} {self.action} {self.model_name}:{self.object_id}"
