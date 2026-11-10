from decimal import Decimal
from rest_framework import serializers
from config.permissions import is_direktur_or_superuser, user_in_group
from core.models import Customer, Supplier
from .models import (
    Product,
    GoodsReceipt,
    GoodsReceiptItem,
    Delivery,
    DeliveryItem,
    StockMovement
)


class RoleFilteredModelSerializer(serializers.ModelSerializer):
    GUDANG_FORBIDDEN_FIELDS = set()
    SALES_FORBIDDEN_FIELDS = set()

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return fields

        if is_direktur_or_superuser(request.user):
            return fields

        if user_in_group(request.user, 'Gudang'):
            for field_name in self.GUDANG_FORBIDDEN_FIELDS:
                fields.pop(field_name, None)

        if user_in_group(request.user, 'Sales'):
            for field_name in self.SALES_FORBIDDEN_FIELDS:
                fields.pop(field_name, None)

        return fields


class ProductSerializer(RoleFilteredModelSerializer):
    estimated_stock_days = serializers.ReadOnlyField()
    is_stock_below_28_days = serializers.ReadOnlyField()

    GUDANG_FORBIDDEN_FIELDS = {'moving_average_hpp', 'selling_price'}
    SALES_FORBIDDEN_FIELDS = {'moving_average_hpp'}

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
            'moving_average_hpp',
            'selling_price',
            'abc_class',
            'daily_consumption_rate',
            'min_stock_level',
            'estimated_stock_days',
            'is_stock_below_28_days',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['current_stock', 'moving_average_hpp', 'abc_class', 'created_at', 'updated_at']


class GoodsReceiptItemSerializer(RoleFilteredModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_uom = serializers.CharField(source='product.uom', read_only=True)
    discrepancy_qty = serializers.ReadOnlyField()

    GUDANG_FORBIDDEN_FIELDS = {'purchase_price', 'allocated_transport_cost', 'effective_unit_cost'}

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
            'effective_unit_cost',
            'discrepancy_qty',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['allocated_transport_cost', 'effective_unit_cost', 'created_at', 'updated_at']


class GoodsReceiptSerializer(RoleFilteredModelSerializer):
    items = GoodsReceiptItemSerializer(many=True, required=False)
    supplier_code = serializers.CharField(source='supplier.code', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    has_quantity_discrepancy = serializers.ReadOnlyField()

    GUDANG_FORBIDDEN_FIELDS = {'transport_cost', 'unloading_cost'}

    class Meta:
        model = GoodsReceipt
        fields = [
            'id',
            'receipt_number',
            'supplier',
            'supplier_code',
            'supplier_name',
            'po_reference',
            'receipt_date',
            'transport_cost',
            'unloading_cost',
            'status',
            'notes',
            'created_by',
            'created_by_name',
            'received_by',
            'received_by_name',
            'confirmed_at',
            'has_quantity_discrepancy',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['status', 'created_by', 'confirmed_at', 'received_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        from config.sequence_generator import generate_document_number
        if not validated_data.get('receipt_number'):
            validated_data['receipt_number'] = generate_document_number('GR', validated_data.get('receipt_date'))
        if self.context.get('request') and self.context.get('request').user.is_authenticated:
            validated_data['created_by'] = self.context.get('request').user
        items_data = self.context.get('request').data.get('items', [])
        receipt = GoodsReceipt.objects.create(**validated_data)
        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            GoodsReceiptItem.objects.create(
                goods_receipt=receipt,
                product=product,
                qty_ordered=item_data['qty_ordered'],
                qty_actual=item_data.get('qty_actual', item_data['qty_ordered']),
                purchase_price=item_data.get('purchase_price', '0.00'),
                notes=item_data.get('notes', '')
            )
        return receipt


class DeliveryItemSerializer(RoleFilteredModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_uom = serializers.CharField(source='product.uom', read_only=True)
    effective_qty = serializers.ReadOnlyField()
    total_cogs = serializers.ReadOnlyField()

    GUDANG_FORBIDDEN_FIELDS = {'hpp_at_delivery', 'total_cogs'}
    SALES_FORBIDDEN_FIELDS = {'hpp_at_delivery', 'total_cogs'}

    class Meta:
        model = DeliveryItem
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'product_uom',
            'qty',
            'qty_delivered',
            'effective_qty',
            'hpp_at_delivery',
            'total_cogs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['hpp_at_delivery', 'created_at', 'updated_at']


class DeliverySerializer(RoleFilteredModelSerializer):
    items = DeliveryItemSerializer(many=True, required=False)
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id',
            'delivery_number',
            'customer',
            'customer_code',
            'customer_name',
            'delivery_date',
            'driver_name',
            'vehicle_number',
            'sales_order_ref',
            'status',
            'confirmed_at',
            'created_by',
            'created_by_name',
            'confirmed_by',
            'confirmed_by_name',
            'notes',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['status', 'created_by', 'confirmed_at', 'confirmed_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        from config.sequence_generator import generate_document_number
        if not validated_data.get('delivery_number'):
            validated_data['delivery_number'] = generate_document_number('SJ', validated_data.get('delivery_date'))
        if self.context.get('request') and self.context.get('request').user.is_authenticated:
            validated_data['created_by'] = self.context.get('request').user
        items_data = self.context.get('request').data.get('items', [])
        delivery = Delivery.objects.create(**validated_data)
        for item_data in items_data:
            product = Product.objects.get(pk=item_data['product'])
            DeliveryItem.objects.create(
                delivery=delivery,
                product=product,
                qty=item_data['qty'],
                qty_delivered=item_data.get('qty_delivered', Decimal('0.00'))
            )
        return delivery


class StockMovementSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_uom = serializers.CharField(source='product.uom', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    reference_type_display = serializers.CharField(source='get_reference_type_display', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id',
            'product',
            'product_sku',
            'product_name',
            'product_uom',
            'movement_date',
            'movement_type',
            'movement_type_display',
            'reference_type',
            'reference_type_display',
            'reference_number',
            'qty',
            'unit_cost',
            'stock_before',
            'stock_after',
            'created_by',
            'created_by_name',
            'notes',
            'created_at',
        ]
        read_only_fields = ['created_at']
