from django.contrib import admin
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


class ProductPriceTierInline(admin.TabularInline):
    model = ProductPriceTier
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'uom', 'current_stock', 'moving_average_hpp', 'selling_price', 'abc_class', 'is_active']
    search_fields = ['sku', 'name', 'brand']
    list_filter = ['abc_class', 'uom', 'is_active']
    inlines = [ProductPriceTierInline]


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'order_date', 'status']
    search_fields = ['po_number', 'supplier__name']
    list_filter = ['status', 'order_date']
    inlines = [PurchaseOrderItemInline]


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 0


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'supplier', 'receipt_date', 'status', 'payable_amount', 'paid_amount', 'payment_status']
    search_fields = ['receipt_number', 'supplier__name']
    list_filter = ['status', 'payment_status', 'receipt_date']
    inlines = [GoodsReceiptItemInline]


class DeliveryItemInline(admin.TabularInline):
    model = DeliveryItem
    extra = 0


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['delivery_number', 'sales_invoice', 'customer', 'delivery_date', 'driver_name', 'status']
    search_fields = ['delivery_number', 'customer__name', 'driver_name', 'vehicle_number']
    list_filter = ['status', 'delivery_date']
    inlines = [DeliveryItemInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['movement_date', 'product', 'movement_type', 'qty', 'stock_before', 'stock_after', 'reference_type', 'reference_id']
    search_fields = ['product__sku', 'product__name', 'reference_id']
    list_filter = ['movement_type', 'movement_date']
    readonly_fields = [f.name for f in StockMovement._meta.fields]
