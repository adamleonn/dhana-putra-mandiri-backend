from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.permissions import IsAccounting, IsDirektur, IsStakeholderReadOnly
from finance.models import DebitNote
from finance.serializers import DebitNoteSerializer
from finance.services.debit_note_service import issue_supplier_debit_note
from inventory.models import GoodsReceipt


class DebitNoteViewSet(viewsets.ModelViewSet):
    queryset = DebitNote.objects.all().select_related(
        'goods_receipt', 'supplier', 'journal_entry', 'period', 'created_by', 'issued_by'
    )
    serializer_class = DebitNoteSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'supplier', 'date']
    search_fields = ['debit_note_number', 'supplier__name', 'reason']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAccounting() | IsDirektur())]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        goods_receipt_id = request.data.get('goods_receipt')
        amount_raw = request.data.get('amount', '0.00')
        reason = request.data.get('reason', '')
        issue_date = request.data.get('date')

        if not goods_receipt_id:
            return Response({'error': "Parameter 'goods_receipt' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        amount = Decimal(str(amount_raw))
        if amount <= Decimal('0.00'):
            return Response({'error': "Nominal klaim Nota Debit harus bernilai positif (> 0)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gr = GoodsReceipt.objects.get(pk=goods_receipt_id)
            dn = issue_supplier_debit_note(
                goods_receipt=gr,
                amount=amount,
                reason=reason,
                issued_by=request.user,
                issue_date=issue_date
            )
            serializer = self.get_serializer(dn)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except GoodsReceipt.DoesNotExist:
            return Response({'error': "Goods Receipt tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
