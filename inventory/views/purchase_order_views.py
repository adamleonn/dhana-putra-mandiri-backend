from rest_framework import viewsets, permissions
from core.permissions import IsAdminOps, IsAccounting, IsDirektur, IsStakeholderReadOnly
from inventory.models import PurchaseOrder
from inventory.serializers import PurchaseOrderSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('supplier', 'created_by').prefetch_related('items__product')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'supplier', 'order_date']
    search_fields = ['po_number', 'supplier__name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAdminOps() | IsAccounting() | IsDirektur())]
        return super().get_permissions()

