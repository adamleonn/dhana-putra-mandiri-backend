from rest_framework import viewsets, permissions
from core.permissions import DEFAULT_PERMISSIONS, READ_ALL, DIREKTUR_ADMIN
from inventory.models import PurchaseOrder
from inventory.serializers import PurchaseOrderSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('supplier', 'created_by').prefetch_related('items__product')
    serializer_class = PurchaseOrderSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': READ_ALL, 'write': DIREKTUR_ADMIN}
    filterset_fields = ['status', 'supplier', 'order_date']
    search_fields = ['po_number', 'supplier__name']


