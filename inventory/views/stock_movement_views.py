from rest_framework import viewsets, permissions
from core.permissions import DEFAULT_PERMISSIONS, READ_ALL
from inventory.models import StockMovement
from inventory.serializers import StockMovementSerializer


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().select_related(
        'product', 'created_by', 'goods_receipt_item', 'delivery_item'
    )
    serializer_class = StockMovementSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': READ_ALL}
    filterset_fields = ['movement_type', 'product', 'reference_type']
    search_fields = ['reference_id', 'product__sku', 'product__name']
