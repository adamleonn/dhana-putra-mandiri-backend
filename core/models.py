from decimal import Decimal
from django.db import models


class DocumentSequenceCounter(models.Model):
    doc_type = models.CharField(max_length=16, db_index=True)
    period_key = models.CharField(max_length=16, db_index=True)
    last_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('doc_type', 'period_key')
        indexes = [
            models.Index(fields=['doc_type', 'period_key']),
        ]
        verbose_name = 'Document Sequence Counter'
        verbose_name_plural = 'Document Sequence Counters'

    def __str__(self):
        return f"{self.doc_type}/{self.period_key}: {self.last_number}"


class Customer(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    contact_person = models.CharField(max_length=128, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Supplier(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    contact_person = models.CharField(max_length=128, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return f"{self.code} - {self.name}"
