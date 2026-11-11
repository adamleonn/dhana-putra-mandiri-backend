from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.permissions import IsFinance, IsAdminOps, IsDirektur, IsStakeholderReadOnly
from finance.models import Payment, SalesInvoice, ChartOfAccounts
from inventory.models import GoodsReceipt
from finance.serializers import PaymentSerializer
from finance.services.payment_service import (
    process_customer_receipt,
    process_supplier_payment,
    process_payroll_payment
)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related(
        'cash_bank_account',
        'sales_invoice__customer',
        'goods_receipt__supplier',
        'debit_note__supplier',
        'payroll_slip__employee',
        'journal_entry',
        'created_by'
    )
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'category', 'direction', 'payment_method', 'payment_date']
    search_fields = ['payment_number', 'reference_number', 'notes']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsFinance() | IsAdminOps() | IsDirektur())]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        category = request.data.get('category')
        payment_method = request.data.get('payment_method', 'bank_transfer')
        cash_bank_account_id = request.data.get('cash_bank_account')
        amount_raw = request.data.get('amount')
        payment_date = request.data.get('payment_date')
        reference_number = request.data.get('reference_number', '')
        notes = request.data.get('notes', '')

        if not cash_bank_account_id or not payment_date:
            return Response(
                {'error': "Parameter 'cash_bank_account' dan 'payment_date' wajib diisi."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cash_bank_account = ChartOfAccounts.objects.get(pk=cash_bank_account_id)
            amount = Decimal(str(amount_raw)) if amount_raw else Decimal('0.00')

            if category == 'customer_receipt':
                sales_invoice_id = request.data.get('sales_invoice')
                if not sales_invoice_id:
                    return Response({'error': "Parameter 'sales_invoice' wajib diisi untuk penerimaan kas piutang."}, status=status.HTTP_400_BAD_REQUEST)
                sales_invoice = SalesInvoice.objects.get(pk=sales_invoice_id)
                payment = process_customer_receipt(
                    sales_invoice=sales_invoice,
                    cash_bank_account=cash_bank_account,
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    actor=request.user,
                    reference_number=reference_number,
                    notes=notes
                )

            elif category == 'supplier_payment':
                goods_receipt_id = request.data.get('goods_receipt')
                if not goods_receipt_id:
                    return Response({'error': "Parameter 'goods_receipt' wajib diisi untuk pembayaran hutang supplier."}, status=status.HTTP_400_BAD_REQUEST)
                goods_receipt = GoodsReceipt.objects.get(pk=goods_receipt_id)
                payment = process_supplier_payment(
                    goods_receipt=goods_receipt,
                    cash_bank_account=cash_bank_account,
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    actor=request.user,
                    reference_number=reference_number,
                    notes=notes
                )

            elif category == 'payroll':
                from hr.models import PayrollSlip
                payroll_slip_id = request.data.get('payroll_slip')
                if not payroll_slip_id:
                    return Response({'error': "Parameter 'payroll_slip' wajib diisi untuk pembayaran gaji."}, status=status.HTTP_400_BAD_REQUEST)
                payroll_slip = PayrollSlip.objects.get(pk=payroll_slip_id)
                payment = process_payroll_payment(
                    payroll_slip=payroll_slip,
                    cash_bank_account=cash_bank_account,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    actor=request.user,
                    reference_number=reference_number,
                    notes=notes
                )
            else:
                return super().create(request, *args, **kwargs)

            serializer = self.get_serializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (ChartOfAccounts.DoesNotExist, SalesInvoice.DoesNotExist, GoodsReceipt.DoesNotExist) as e:
            return Response({'error': f"Entitas referensi tidak ditemukan: {str(e)}"}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
