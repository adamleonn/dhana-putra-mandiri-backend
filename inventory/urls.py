from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    GoodsReceiptViewSet,
    DeliveryViewSet,
    StockMovementViewSet,
    PurchaseOrderViewSet
)

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register('goods-receipts', GoodsReceiptViewSet, basename='goods-receipt')
router.register('deliveries', DeliveryViewSet, basename='delivery')
router.register('stock-movements', StockMovementViewSet, basename='stock-movement')

urlpatterns = [
    path('', include(router.urls)),
]
