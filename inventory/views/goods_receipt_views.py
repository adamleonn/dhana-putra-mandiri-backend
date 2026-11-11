from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.permissions import IsGudang, IsDirektur, IsAdminOps, IsAccounting, IsStakeholderReadOnly
from inventory.models import GoodsReceipt
from inventory.serializers import GoodsReceiptSerializer
from inventory.services.hpp_service import confirm_goods_receipt


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.all().select_related(
        'supplier', 'purchase_order', 'created_by', 'received_by', 'confirmed_by'
    ).prefetch_related('items__product')
    serializer_class = GoodsReceiptSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'payment_status', 'supplier', 'receipt_date']
    search_fields = ['receipt_number', 'supplier__name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), (IsAdminOps() | IsAccounting() | IsDirektur())]
        if self.action == 'confirm':
            return [permissions.IsAuthenticated(), (IsGudang() | IsDirektur())]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        receipt = self.get_object()
        try:
            confirmed_receipt = confirm_goods_receipt(receipt, request.user)
            serializer = self.get_serializer(confirmed_receipt)
            return Response(
                {
                    'message': 'Penerimaan barang (BPB) berhasil dikonfirmasi. Stok fisik dan HPP telah dimutasi.',
                    'status': confirmed_receipt.status,
                    'has_discrepancy': confirmed_receipt.has_quantity_discrepancy,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response(
                {
                    'code': 'VALIDATION_ERROR',
                    'message': str(ve)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
