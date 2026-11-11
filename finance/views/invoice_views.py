from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.permissions import IsSales, IsAdminOps, IsAccounting, IsDirektur, IsStakeholderReadOnly
from finance.models import SalesInvoice
from finance.serializers import SalesInvoiceSerializer, SalesInvoiceRevisionSerializer
from finance.services.revision_service import revise_sales_invoice_shortage


class SalesInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SalesInvoice.objects.all().select_related(
        'customer', 'created_by', 'journal_entry', 'delivery'
    ).prefetch_related('items__product', 'revisions__revised_by')
    serializer_class = SalesInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'customer', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'customer__name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), (IsSales() | IsAdminOps() | IsDirektur())]
        return super().get_permissions()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsAccounting | IsDirektur])
    def revise(self, request, pk=None):
        invoice = self.get_object()
        new_subtotal = request.data.get('new_subtotal')
        reason = request.data.get('reason', '')

        if new_subtotal is None or not reason:
            return Response(
                {'error': "Parameter 'new_subtotal' dan 'reason' wajib disertakan."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            revision = revise_sales_invoice_shortage(
                invoice=invoice,
                new_subtotal=Decimal(str(new_subtotal)),
                reason=reason,
                revised_by=request.user
            )
            serializer = SalesInvoiceRevisionSerializer(revision)
            return Response(
                {
                    'message': f"Faktur {invoice.invoice_number} berhasil direvisi.",
                    'revision': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
