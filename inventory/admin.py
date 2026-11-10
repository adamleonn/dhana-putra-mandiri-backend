from django.contrib import admin
from .models import Product, GoodsReceipt, GoodsReceiptItem, Delivery, DeliveryItem, StockMovement


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 0
    fields = ('product', 'qty_ordered', 'qty_actual', 'purchase_price', 'allocated_transport_cost', 'effective_unit_cost')
    readonly_fields = ('allocated_transport_cost', 'effective_unit_cost')


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'supplier', 'supplier_name', 'receipt_date', 'transport_cost', 'unloading_cost', 'status', 'received_by')
    list_filter = ('status', 'receipt_date')
    search_fields = ('receipt_number', 'supplier_name', 'po_reference')
    inlines = [GoodsReceiptItemInline]


class DeliveryItemInline(admin.TabularInline):
    model = DeliveryItem
    extra = 0
    fields = ('product', 'qty', 'qty_delivered', 'hpp_at_delivery')
    readonly_fields = ('hpp_at_delivery',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_number', 'customer', 'customer_name', 'delivery_date', 'status', 'driver_name', 'confirmed_by')
    list_filter = ('status', 'delivery_date')
    search_fields = ('delivery_number', 'customer_name', 'sales_order_ref')
    inlines = [DeliveryItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'uom', 'current_stock', 'moving_average_hpp', 'selling_price', 'abc_class', 'daily_consumption_rate', 'is_active')
    list_filter = ('abc_class', 'uom', 'is_active')
    search_fields = ('sku', 'name')
    readonly_fields = ('current_stock', 'moving_average_hpp', 'abc_class')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('movement_date', 'product', 'movement_type', 'reference_type', 'reference_number', 'qty', 'unit_cost', 'stock_before', 'stock_after')
    list_filter = ('movement_type', 'reference_type', 'movement_date')
    search_fields = ('reference_number', 'product__sku', 'product__name')
    readonly_fields = ('movement_date', 'created_at')
