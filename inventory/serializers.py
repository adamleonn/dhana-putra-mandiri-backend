from decimal import Decimal
from rest_framework import serializers
from core.mixins import RoleFilteredSerializerMixin
from core.services.sequence import next_number
from inventory.models import (
    Product,
    ProductPriceTier,
    PurchaseOrder,
    PurchaseOrderItem,
    GoodsReceipt,
    GoodsReceiptItem,
    Delivery,
    DeliveryItem,
    StockMovement
)


class ProductPriceTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPriceTier
        fields = ['id', 'product', 'min_qty', 'price', 'effective_from']


class ProductSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    estimated_days_of_stock = serializers.ReadOnlyField()
    price_tiers = ProductPriceTierSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'brand',
            'package_size',
            'description',
            'uom',
            'base_unit',
            'conversion_factor',
            'current_stock',
            'stock_value',
            'moving_average_hpp',
            'selling_price',
            'lead_time_days',
            'abc_class',
            'daily_consumption_rate',
            'min_stock_level',
            'estimated_days_of_stock',
            'price_tiers',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['stock_value', 'moving_average_hpp', 'created_at', 'updated_at']


class PurchaseOrderItemSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'qty_ordered',
            'unit_price',
            'line_total'
        ]
        read_only_fields = ['line_total']


class PurchaseOrderSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, required=False)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'po_number',
            'supplier',
            'supplier_name',
            'order_date',
            'status',
            'notes',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['po_number', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        items_data = self.context.get('request').data.get('items', [])
        order_date = validated_data.get('order_date')
        validated_data['po_number'] = next_number('PO', order_date)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user

        po = PurchaseOrder.objects.create(**validated_data)
        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=product,
                qty_ordered=Decimal(str(item_data['qty_ordered'])),
                unit_price=Decimal(str(item_data.get('unit_price', product.moving_average_hpp)))
            )
        return po


class GoodsReceiptItemSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_uom = serializers.CharField(source='product.uom', read_only=True)
    discrepancy_qty = serializers.ReadOnlyField()

    class Meta:
        model = GoodsReceiptItem
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'product_uom',
            'qty_ordered',
            'qty_actual',
            'purchase_price',
            'allocated_transport_cost',
            'allocated_unloading_cost',
            'effective_unit_cost',
            'line_total',
            'discrepancy_qty',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'allocated_transport_cost',
            'allocated_unloading_cost',
            'effective_unit_cost',
            'line_total',
            'created_at',
            'updated_at'
        ]


class GoodsReceiptSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, required=False)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    net_payable = serializers.ReadOnlyField()
    has_quantity_discrepancy = serializers.ReadOnlyField()

    class Meta:
        model = GoodsReceipt
        fields = [
            'id',
            'receipt_number',
            'purchase_order',
            'supplier',
            'supplier_code',
            'supplier_name',
            'receipt_date',
            'due_date',
            'payment_method',
            'payment_status',
            'transport_cost',
            'unloading_cost',
            'payable_amount',
            'debit_note_total',
            'paid_amount',
            'net_payable',
            'status',
            'notes',
            'has_quantity_discrepancy',
            'confirmed_at',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'receipt_number',
            'status',
            'payment_status',
            'payable_amount',
            'debit_note_total',
            'paid_amount',
            'confirmed_at',
            'created_at',
            'updated_at'
        ]

    def create(self, validated_data):
        receipt_date = validated_data.get('receipt_date')
        validated_data['receipt_number'] = next_number('GR', receipt_date)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['received_by'] = request.user

        items_data = self.context.get('request').data.get('items', [])
        po = validated_data.get('purchase_order')

        receipt = GoodsReceipt.objects.create(**validated_data)
        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            qty_ordered = item_data.get('qty_ordered')
            if po and not qty_ordered:
                po_item = po.items.filter(product=product).first()
                qty_ordered = po_item.qty_ordered if po_item else item_data['qty_actual']
            elif not qty_ordered:
                qty_ordered = item_data['qty_actual']

            GoodsReceiptItem.objects.create(
                goods_receipt=receipt,
                product=product,
                qty_ordered=Decimal(str(qty_ordered)),
                qty_actual=Decimal(str(item_data['qty_actual'])),
                purchase_price=Decimal(str(item_data.get('purchase_price', '0.00'))),
                notes=item_data.get('notes', '')
            )
        return receipt


class DeliveryItemSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_uom = serializers.CharField(source='product.uom', read_only=True)
    effective_qty = serializers.ReadOnlyField()

    class Meta:
        model = DeliveryItem
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'product_uom',
            'sales_invoice_item',
            'qty',
            'qty_delivered',
            'effective_qty',
            'hpp_at_delivery',
            'total_cogs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['hpp_at_delivery', 'total_cogs', 'created_at', 'updated_at']


class DeliverySerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    items = DeliveryItemSerializer(many=True, required=False)
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    invoice_number = serializers.CharField(source='sales_invoice.invoice_number', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id',
            'delivery_number',
            'sales_invoice',
            'invoice_number',
            'customer',
            'customer_code',
            'customer_name',
            'delivery_date',
            'driver_name',
            'vehicle_number',
            'status',
            'confirmed_at',
            'notes',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['delivery_number', 'status', 'confirmed_at', 'created_at', 'updated_at']

    def create(self, validated_data):
        delivery_date = validated_data.get('delivery_date')
        validated_data['delivery_number'] = next_number('SJ', delivery_date)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user

        items_data = self.context.get('request').data.get('items', [])
        delivery = Delivery.objects.create(**validated_data)

        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            inv_item_id = item_data.get('sales_invoice_item')
            DeliveryItem.objects.create(
                delivery=delivery,
                product=product,
                sales_invoice_item_id=inv_item_id,
                qty=Decimal(str(item_data['qty'])),
                qty_delivered=None
            )
        return delivery


class StockMovementSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'movement_date',
            'movement_type',
            'qty',
            'unit_cost',
            'total_cost',
            'stock_before',
            'stock_after',
            'hpp_after',
            'goods_receipt_item',
            'delivery_item',
            'reference_type',
            'reference_id',
            'notes',
            'created_at',
        ]
        read_only_fields = fields
