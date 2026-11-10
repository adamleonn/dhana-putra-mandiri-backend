from django.contrib import admin
from .models import (
    ChartOfAccounts,
    AccountingPeriod,
    GeneralLedger,
    GeneralLedgerLine,
    SalesInvoice,
    SalesInvoiceItem,
    DebitNote,
    Payment
)


@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ('period_name', 'start_date', 'end_date', 'status', 'closed_by', 'closed_at')
    list_filter = ('status',)
    search_fields = ('period_name',)


class GeneralLedgerLineInline(admin.TabularInline):
    model = GeneralLedgerLine
    extra = 0
    fields = ('account', 'debit', 'credit', 'memo')


@admin.register(GeneralLedger)
class GeneralLedgerAdmin(admin.ModelAdmin):
    list_display = ('entry_number', 'transaction_date', 'reference_type', 'reference_id', 'is_posted', 'created_by', 'posted_by')
    list_filter = ('reference_type', 'is_posted', 'transaction_date')
    search_fields = ('entry_number', 'reference_id', 'description')
    inlines = [GeneralLedgerLineInline]


class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    extra = 0
    fields = ('product', 'qty_ordered', 'qty_delivered', 'qty', 'unit_price', 'discount_amount', 'line_total')
    readonly_fields = ('line_total',)


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'customer', 'customer_name', 'invoice_date', 'total_amount', 'paid_amount', 'status', 'created_by')
    list_filter = ('status', 'invoice_date')
    search_fields = ('invoice_number', 'customer_name')
    inlines = [SalesInvoiceItemInline]


@admin.register(DebitNote)
class DebitNoteAdmin(admin.ModelAdmin):
    list_display = ('debit_note_number', 'supplier', 'supplier_name', 'date', 'amount', 'status', 'created_by', 'issued_by')
    list_filter = ('status', 'date')
    search_fields = ('debit_note_number', 'supplier_name', 'reason')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_number', 'payment_type', 'category', 'customer', 'supplier', 'cash_bank_account', 'amount', 'payment_date', 'status')
    list_filter = ('payment_type', 'category', 'status', 'payment_date')
    search_fields = ('payment_number', 'reference_number')
