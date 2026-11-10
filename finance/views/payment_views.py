from rest_framework import viewsets, permissions
from config.permissions import IsFinanceKasir, IsDirekturOrSuperuser
from finance.models import Payment
from finance.serializers import PaymentSerializer
from finance.services import validate_supplier_payment_permission


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related(
        'cash_bank_account',
        'customer',
        'supplier',
        'sales_invoice',
        'goods_receipt',
        'debit_note',
        'journal_entry',
        'created_by'
    )
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, (IsFinanceKasir | IsDirekturOrSuperuser)]

    def perform_create(self, serializer):
        goods_receipt = serializer.validated_data.get('goods_receipt')
        amount = serializer.validated_data.get('amount')
        category = serializer.validated_data.get('category')

        if category == 'supplier_payment' and goods_receipt:
            validate_supplier_payment_permission(goods_receipt, amount)

        serializer.save(created_by=self.request.user)
