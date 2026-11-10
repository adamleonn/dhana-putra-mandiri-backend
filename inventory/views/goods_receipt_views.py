from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from config.permissions import StrictRoleBasedAccess, IsWarehouseStaff, IsDirekturOrSuperuser
from inventory.models import GoodsReceipt
from inventory.serializers import GoodsReceiptSerializer
from inventory.services import confirm_goods_receipt


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all().select_related('supplier', 'created_by', 'received_by').prefetch_related('items__product')
    serializer_class = GoodsReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

    @action(detail=True, methods=['post'], permission_classes=[IsWarehouseStaff | IsDirekturOrSuperuser])
    def confirm(self, request, pk=None):
        receipt = self.get_object()
        try:
            confirmed_receipt = confirm_goods_receipt(receipt, request.user)
            serializer = self.get_serializer(confirmed_receipt)
            return Response(
                {
                    'message': 'Goods Receipt confirmed successfully. Inventory stock & HPP updated.',
                    'status': confirmed_receipt.status,
                    'has_discrepancy': confirmed_receipt.has_quantity_discrepancy,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
