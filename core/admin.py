from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models import User, Customer, Supplier, DocumentSequenceCounter, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('OIDC Identity', {'fields': ('oidc_issuer', 'oidc_subject')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'oidc_issuer']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'oidc_subject']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'phone', 'credit_limit', 'payment_term_days', 'is_active']
    search_fields = ['code', 'name', 'phone', 'email', 'tax_id']
    list_filter = ['is_active']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'phone', 'payment_term_days', 'is_active']
    search_fields = ['code', 'name', 'phone', 'email', 'tax_id']
    list_filter = ['is_active']


@admin.register(DocumentSequenceCounter)
class DocumentSequenceCounterAdmin(admin.ModelAdmin):
    list_display = ['doc_type', 'period_key', 'last_number', 'updated_at']
    list_filter = ['doc_type', 'period_key']
    search_fields = ['doc_type', 'period_key']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'actor', 'action', 'model_name', 'object_id', 'ip_address']
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['object_id', 'object_repr', 'request_id']
    readonly_fields = ['created_at', 'actor', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'ip_address', 'request_id']
