from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from config.permissions import StrictRoleBasedAccess, IsWarehouseStaff, IsDirekturOrSuperuser
from inventory.models import Delivery
from inventory.serializers import DeliverySerializer
from inventory.services import confirm_delivery_atomic, InsufficientStockError


class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all().select_related('customer', 'created_by', 'confirmed_by').prefetch_related('items__product')
    serializer_class = DeliverySerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

    @action(detail=True, methods=['post'], permission_classes=[IsWarehouseStaff | IsDirekturOrSuperuser])
    def confirm(self, request, pk=None):
        delivery = self.get_object()
        try:
            confirmed_delivery = confirm_delivery_atomic(delivery, request.user)
            serializer = self.get_serializer(confirmed_delivery)
            return Response(
                {
                    'message': 'Delivery confirmed. Stock deducted and double-entry journals posted.',
                    'delivery_number': confirmed_delivery.delivery_number,
                    'status': confirmed_delivery.status,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except InsufficientStockError as ise:
            return Response(
                {
                    'error': 'Insufficient Stock Conflict',
                    'detail': str(ise),
                    'sku': ise.product_sku,
                    'product_name': ise.product_name,
                    'requested_qty': str(ise.requested_qty),
                    'available_stock': str(ise.available_stock)
                },
                status=status.HTTP_409_CONFLICT
            )
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
