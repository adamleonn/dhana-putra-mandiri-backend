from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.permissions import IsGudang, IsDirektur, IsSales, IsAdminOps, IsStakeholderReadOnly
from inventory.models import Delivery
from inventory.serializers import DeliverySerializer
from inventory.services.delivery_service import confirm_delivery_atomic
from config.exceptions import InsufficientStockError


class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all().select_related(
        'sales_invoice', 'customer', 'created_by', 'confirmed_by'
    ).prefetch_related('items__product', 'items__sales_invoice_item')
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'customer', 'delivery_date']
    search_fields = ['delivery_number', 'customer__name', 'driver_name', 'vehicle_number']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), (IsSales() | IsAdminOps() | IsDirektur())]
        if self.action == 'confirm':
            return [permissions.IsAuthenticated(), (IsGudang() | IsDirektur())]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        delivery = self.get_object()

        # Update actual delivered quantities if provided in confirmation payload
        items_payload = request.data.get('items', [])
        if items_payload:
            for it in items_payload:
                line_id = it.get('id')
                qty_del = it.get('qty_delivered')
                if line_id is not None and qty_del is not None:
                    delivery.items.filter(id=line_id).update(qty_delivered=Decimal(str(qty_del)))

        try:
            confirmed_delivery = confirm_delivery_atomic(delivery, request.user)
            serializer = self.get_serializer(confirmed_delivery)
            return Response(
                {
                    'message': 'Surat Jalan berhasil dikonfirmasi. Stok fisik terpotong dan jurnal HPP diterbitkan.',
                    'delivery_number': confirmed_delivery.delivery_number,
                    'status': confirmed_delivery.status,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except InsufficientStockError as ise:
            return Response(
                {
                    'code': 'INSUFFICIENT_STOCK',
                    'message': str(ise),
                    'details': {
                        'sku': ise.product_sku,
                        'product_name': ise.product_name,
                        'requested_qty': str(ise.requested_qty),
                        'available_stock': str(ise.available_stock)
                    }
                },
                status=status.HTTP_409_CONFLICT
            )
        except ValidationError as ve:
            return Response(
                {
                    'code': 'VALIDATION_ERROR',
                    'message': str(ve)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
