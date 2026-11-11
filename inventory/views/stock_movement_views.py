from rest_framework import viewsets, permissions
from core.permissions import IsStakeholderReadOnly
from inventory.models import StockMovement
from inventory.serializers import StockMovementSerializer


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.all().select_related(
        'product', 'created_by', 'goods_receipt_item', 'delivery_item'
    )
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['movement_type', 'product', 'reference_type']
    search_fields = ['reference_id', 'product__sku', 'product__name']
