from decimal import Decimal
from rest_framework import serializers
from config.permissions import is_direktur_or_superuser, user_in_group
from core.models import Customer, Supplier
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
from inventory.models import Product


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id',
            'code',
            'name',
            'contact_person',
            'phone',
            'email',
            'address',
            'credit_limit',
            'is_active',
            'created_at',
            'updated_at',
        ]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id',
            'code',
            'name',
            'contact_person',
            'phone',
            'email',
            'address',
            'is_active',
            'created_at',
            'updated_at',
        ]


class ChartOfAccountsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartOfAccounts
        fields = [
            'id',
            'code',
            'name',
            'account_type',
            'is_active',
            'description',
            'created_at',
            'updated_at',
        ]


class AccountingPeriodSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.CharField(source='closed_by.get_full_name', read_only=True)
    reopened_by_name = serializers.CharField(source='reopened_by.get_full_name', read_only=True)
    is_closed = serializers.ReadOnlyField()

    class Meta:
        model = AccountingPeriod
        fields = [
            'id',
            'period_name',
            'start_date',
            'end_date',
            'status',
            'is_closed',
            'closed_by',
            'closed_by_name',
            'closed_at',
            'reopened_by',
            'reopened_by_name',
            'reopened_at',
            'reopen_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['status', 'closed_by', 'closed_at', 'reopened_by', 'reopened_at', 'created_at', 'updated_at']


class GeneralLedgerLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = GeneralLedgerLine
        fields = [
            'id',
            'account',
            'account_code',
            'account_name',
            'debit',
            'credit',
            'memo',
            'created_at',
            'updated_at',
        ]


class GeneralLedgerSerializer(serializers.ModelSerializer):
    lines = GeneralLedgerLineSerializer(many=True, read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    total_debit = serializers.ReadOnlyField()
    total_credit = serializers.ReadOnlyField()
    is_balanced = serializers.ReadOnlyField()

    class Meta:
        model = GeneralLedger
        fields = [
            'id',
            'entry_number',
            'transaction_date',
            'period',
            'reference_type',
            'reference_id',
            'description',
            'is_posted',
            'created_by',
            'created_by_name',
            'posted_by',
            'posted_by_name',
            'total_debit',
            'total_credit',
            'is_balanced',
            'lines',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['entry_number', 'is_posted', 'created_by', 'posted_by', 'created_at', 'updated_at']


class SalesInvoiceItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SalesInvoiceItem
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'qty_ordered',
            'qty_delivered',
            'qty',
            'unit_price',
            'discount_amount',
            'line_total',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['line_total', 'created_at', 'updated_at']


class SalesInvoiceSerializer(serializers.ModelSerializer):
    items = SalesInvoiceItemSerializer(many=True, required=False)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    remaining_balance = serializers.ReadOnlyField()

    class Meta:
        model = SalesInvoice
        fields = [
            'id',
            'invoice_number',
            'delivery',
            'customer',
            'customer_code',
            'customer_name',
            'invoice_date',
            'due_date',
            'subtotal',
            'discount_amount',
            'total_amount',
            'paid_amount',
            'remaining_balance',
            'status',
            'created_by',
            'created_by_name',
            'notes',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['paid_amount', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        from config.sequence_generator import generate_document_number
        if not validated_data.get('invoice_number'):
            validated_data['invoice_number'] = generate_document_number('INV', validated_data.get('invoice_date'))

        items_data = self.context.get('request').data.get('items', [])
        subtotal = Decimal('0.00')
        lines_to_create = []

        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            qty_ordered = Decimal(str(item_data.get('qty_ordered', item_data.get('qty', '0.00'))))
            qty_delivered = Decimal(str(item_data.get('qty_delivered', qty_ordered)))
            qty = qty_delivered
            unit_price = Decimal(str(item_data.get('unit_price', product.selling_price)))
            line_disc = Decimal(str(item_data.get('discount_amount', '0.00')))
            line_total = (qty * unit_price) - line_disc
            subtotal += line_total
            lines_to_create.append({
                'product': product,
                'qty_ordered': qty_ordered,
                'qty_delivered': qty_delivered,
                'qty': qty,
                'unit_price': unit_price,
                'discount_amount': line_disc,
                'line_total': line_total
            })

        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))
        validated_data['subtotal'] = subtotal
        validated_data['total_amount'] = max(Decimal('0.00'), subtotal - discount_amount)
        if self.context.get('request') and self.context.get('request').user.is_authenticated:
            validated_data['created_by'] = self.context.get('request').user

        invoice = SalesInvoice.objects.create(**validated_data)
        for line in lines_to_create:
            SalesInvoiceItem.objects.create(invoice=invoice, **line)

        return invoice


class DebitNoteSerializer(serializers.ModelSerializer):
    issued_by_name = serializers.CharField(source='issued_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    goods_receipt_number = serializers.CharField(source='goods_receipt.receipt_number', read_only=True)

    class Meta:
        model = DebitNote
        fields = [
            'id',
            'debit_note_number',
            'goods_receipt',
            'goods_receipt_number',
            'supplier',
            'supplier_code',
            'supplier_name',
            'date',
            'amount',
            'reason',
            'status',
            'journal_entry',
            'created_by',
            'created_by_name',
            'issued_by',
            'issued_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['journal_entry', 'created_by', 'issued_by', 'created_at', 'updated_at']


class PaymentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    customer_name_display = serializers.CharField(source='customer.name', read_only=True)
    supplier_name_display = serializers.CharField(source='supplier.name', read_only=True)
    cash_bank_account_code = serializers.CharField(source='cash_bank_account.code', read_only=True)
    cash_bank_account_name = serializers.CharField(source='cash_bank_account.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_number',
            'payment_type',
            'category',
            'cash_bank_account',
            'cash_bank_account_code',
            'cash_bank_account_name',
            'customer',
            'customer_name_display',
            'supplier',
            'supplier_name_display',
            'sales_invoice',
            'goods_receipt',
            'debit_note',
            'amount',
            'payment_date',
            'reference_number',
            'status',
            'notes',
            'journal_entry',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['journal_entry', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        from config.sequence_generator import generate_document_number
        if not validated_data.get('payment_number'):
            category = validated_data.get('category')
            prefix = 'BKM' if category == 'customer_receipt' else 'BKK'
            validated_data['payment_number'] = generate_document_number(prefix, validated_data.get('payment_date'))
        if self.context.get('request') and self.context.get('request').user.is_authenticated:
            validated_data['created_by'] = self.context.get('request').user
        return super().create(validated_data)
