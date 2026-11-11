from decimal import Decimal
from rest_framework import serializers
from core.mixins import RoleFilteredSerializerMixin
from core.services.sequence import next_number
from inventory.models import Product, ProductPriceTier
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


class ChartOfAccountsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartOfAccounts
        fields = [
            'id',
            'account_code',
            'name',
            'account_type',
            'parent',
            'report_group',
            'normal_balance',
            'is_cash_bank',
            'is_postable',
            'is_active',
            'created_at',
            'updated_at',
        ]


class AccountingPeriodSerializer(serializers.ModelSerializer):
    is_closed = serializers.BooleanField(read_only=True)
    closed_by_name = serializers.CharField(source='closed_by.get_full_name', read_only=True)
    reopened_by_name = serializers.CharField(source='reopened_by.get_full_name', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)

    class Meta:
        model = AccountingPeriod
        fields = [
            'id',
            'period_name',
            'start_date',
            'end_date',
            'status',
            'is_closed',
            'submitted_by',
            'submitted_by_name',
            'submitted_at',
            'closed_by',
            'closed_by_name',
            'closed_at',
            'reopened_by',
            'reopened_by_name',
            'reopened_at',
            'closing_notes',
            'reopen_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'status', 'is_closed', 'submitted_by', 'submitted_at',
            'closed_by', 'closed_at', 'reopened_by', 'reopened_at',
            'created_at', 'updated_at'
        ]


class GeneralLedgerLineSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.account_code', read_only=True)
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
        ]


class GeneralLedgerSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    lines = GeneralLedgerLineSerializer(many=True, read_only=True)
    period_name = serializers.CharField(source='period.period_name', read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.get_full_name', read_only=True)

    class Meta:
        model = GeneralLedger
        fields = [
            'id',
            'transaction_number',
            'period',
            'period_name',
            'date',
            'reference_type',
            'reference_id',
            'description',
            'is_posted',
            'reversal_of',
            'posted_by',
            'posted_by_name',
            'lines',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class SalesInvoiceItemSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    effective_billed_qty = serializers.ReadOnlyField()

    class Meta:
        model = SalesInvoiceItem
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'qty_ordered',
            'qty_delivered',
            'effective_billed_qty',
            'unit_price',
            'discount_amount',
            'line_total',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['qty_delivered', 'line_total', 'created_at', 'updated_at']


class SalesInvoiceRevisionSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    revised_by_name = serializers.CharField(source='revised_by.get_full_name', read_only=True)

    class Meta:
        model = SalesInvoiceRevision
        fields = [
            'id',
            'invoice',
            'revision_number',
            'old_total',
            'new_total',
            'reason',
            'revised_by',
            'revised_by_name',
            'created_at',
        ]
        read_only_fields = fields


class SalesInvoiceSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    items = SalesInvoiceItemSerializer(many=True, required=False)
    revisions = SalesInvoiceRevisionSerializer(many=True, read_only=True)
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    remaining_due = serializers.ReadOnlyField()

    class Meta:
        model = SalesInvoice
        fields = [
            'id',
            'invoice_number',
            'customer',
            'customer_code',
            'customer_name',
            'invoice_date',
            'due_date',
            'payment_method',
            'subtotal',
            'discount_amount',
            'total_amount',
            'paid_amount',
            'remaining_due',
            'status',
            'revision_no',
            'notes',
            'journal_entry',
            'items',
            'revisions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'invoice_number',
            'subtotal',
            'total_amount',
            'paid_amount',
            'status',
            'revision_no',
            'journal_entry',
            'created_at',
            'updated_at'
        ]

    def create(self, validated_data):
        invoice_date = validated_data.get('invoice_date')
        validated_data['invoice_number'] = next_number('INV', invoice_date)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user

        items_data = self.context.get('request').data.get('items', [])
        subtotal = Decimal('0.00')

        # Calculate initial subtotal
        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            qty_ordered = Decimal(str(item_data['qty_ordered']))
            unit_price = item_data.get('unit_price')
            if not unit_price:
                tier = ProductPriceTier.objects.filter(
                    product=product,
                    min_qty__lte=qty_ordered,
                    effective_from__lte=invoice_date
                ).order_by('-min_qty').first()
                unit_price = tier.price if tier else product.selling_price
            else:
                unit_price = Decimal(str(unit_price))

            disc = Decimal(str(item_data.get('discount_amount', '0.00')))
            line_tot = max(Decimal('0.00'), (qty_ordered * unit_price) - disc)
            subtotal += line_tot

        discount_amount = validated_data.get('discount_amount', Decimal('0.00'))
        validated_data['subtotal'] = subtotal
        validated_data['total_amount'] = max(Decimal('0.00'), subtotal - discount_amount)
        validated_data['status'] = 'draft'

        invoice = SalesInvoice.objects.create(**validated_data)

        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            qty_ordered = Decimal(str(item_data['qty_ordered']))
            unit_price = item_data.get('unit_price')
            if not unit_price:
                tier = ProductPriceTier.objects.filter(
                    product=product,
                    min_qty__lte=qty_ordered,
                    effective_from__lte=invoice_date
                ).order_by('-min_qty').first()
                unit_price = tier.price if tier else product.selling_price
            else:
                unit_price = Decimal(str(unit_price))

            disc = Decimal(str(item_data.get('discount_amount', '0.00')))
            line_tot = max(Decimal('0.00'), (qty_ordered * unit_price) - disc)

            SalesInvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                qty_ordered=qty_ordered,
                qty_delivered=None,
                unit_price=unit_price,
                discount_amount=disc,
                line_total=line_tot
            )

        return invoice


class DebitNoteSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    receipt_number = serializers.CharField(source='goods_receipt.receipt_number', read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.get_full_name', read_only=True)

    class Meta:
        model = DebitNote
        fields = [
            'id',
            'debit_note_number',
            'goods_receipt',
            'receipt_number',
            'supplier',
            'supplier_name',
            'date',
            'amount',
            'reason',
            'status',
            'journal_entry',
            'period',
            'issued_by',
            'issued_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'debit_note_number',
            'status',
            'journal_entry',
            'period',
            'issued_by',
            'created_at',
            'updated_at'
        ]


class PaymentSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    cash_bank_name = serializers.CharField(source='cash_bank_account.name', read_only=True)
    invoice_number = serializers.CharField(source='sales_invoice.invoice_number', read_only=True)
    receipt_number = serializers.CharField(source='goods_receipt.receipt_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_number',
            'payment_method',
            'category',
            'direction',
            'cash_bank_account',
            'cash_bank_name',
            'sales_invoice',
            'invoice_number',
            'goods_receipt',
            'receipt_number',
            'debit_note',
            'payroll_slip',
            'amount',
            'payment_date',
            'reference_number',
            'status',
            'notes',
            'journal_entry',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['payment_number', 'direction', 'status', 'journal_entry', 'created_at', 'updated_at']
