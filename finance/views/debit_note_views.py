from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from config.permissions import IsAccountingStaff, IsDirekturOrSuperuser
from finance.models import DebitNote
from finance.serializers import DebitNoteSerializer
from finance.services import issue_supplier_debit_note


class DebitNoteViewSet(viewsets.ModelViewSet):
    queryset = DebitNote.objects.all().select_related('goods_receipt', 'supplier', 'journal_entry', 'created_by', 'issued_by')
    serializer_class = DebitNoteSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccountingStaff | IsDirekturOrSuperuser)]

    def create(self, request, *args, **kwargs):
        from inventory.models import GoodsReceipt
        goods_receipt_id = request.data.get('goods_receipt')
        amount = Decimal(str(request.data.get('amount', '0.00')))
        reason = request.data.get('reason', '')
        debit_note_number = request.data.get('debit_note_number')

        if not goods_receipt_id or amount <= Decimal('0.00'):
            return Response(
                {'error': 'goods_receipt and positive amount are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            gr = GoodsReceipt.objects.get(pk=goods_receipt_id)
            dn = issue_supplier_debit_note(
                goods_receipt=gr,
                amount=amount,
                reason=reason,
                issued_by=request.user,
                debit_note_number=debit_note_number
            )
            serializer = self.get_serializer(dn)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except GoodsReceipt.DoesNotExist:
            return Response({'error': 'Goods Receipt not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
