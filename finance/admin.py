from django.contrib import admin
from finance.models import (
    ChartOfAccounts,
    AccountingPeriod,
    GeneralLedger,
    GeneralLedgerLine,
    SalesInvoice,
    SalesInvoiceItem,
    SalesInvoiceRevision,
    DebitNote,
    Payment
)


@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ['account_code', 'name', 'account_type', 'report_group', 'normal_balance', 'is_cash_bank', 'is_postable', 'is_active']
    search_fields = ['account_code', 'name']
    list_filter = ['account_type', 'report_group', 'is_cash_bank', 'is_postable', 'is_active']


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ['period_name', 'start_date', 'end_date', 'status', 'closed_by', 'closed_at']
    list_filter = ['status', 'start_date']
    search_fields = ['period_name']


class GeneralLedgerLineInline(admin.TabularInline):
    model = GeneralLedgerLine
    extra = 0
    readonly_fields = ['account', 'debit', 'credit', 'memo']


@admin.register(GeneralLedger)
class GeneralLedgerAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'date', 'period', 'reference_type', 'reference_id', 'is_posted', 'posted_by']
    search_fields = ['transaction_number', 'reference_id', 'description']
    list_filter = ['reference_type', 'date', 'is_posted']
    inlines = [GeneralLedgerLineInline]
    readonly_fields = [f.name for f in GeneralLedger._meta.fields]


class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 0


class SalesInvoiceRevisionInline(admin.TabularInline):
    model = SalesInvoiceRevision
    extra = 0
    readonly_fields = ['revision_number', 'old_total', 'new_total', 'reason', 'revised_by', 'created_at']


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'invoice_date', 'due_date', 'total_amount', 'paid_amount', 'status', 'revision_no']
    search_fields = ['invoice_number', 'customer__name']
    list_filter = ['status', 'payment_method', 'invoice_date']
    inlines = [SalesInvoiceItemInline, SalesInvoiceRevisionInline]


@admin.register(DebitNote)
class DebitNoteAdmin(admin.ModelAdmin):
    list_display = ['debit_note_number', 'supplier', 'goods_receipt', 'date', 'amount', 'status', 'issued_by']
    search_fields = ['debit_note_number', 'supplier__name']
    list_filter = ['status', 'date']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_number', 'payment_method', 'category', 'direction', 'cash_bank_account', 'amount', 'payment_date', 'status']
    search_fields = ['payment_number', 'reference_number']
    list_filter = ['status', 'category', 'direction', 'payment_method', 'payment_date']
