from decimal import Decimal
from django.core.exceptions import ValidationError


def validate_supplier_payment_permission(goods_receipt, proposed_payment_amount: Decimal):
    if goods_receipt.has_quantity_discrepancy:
        active_dn = goods_receipt.debit_notes.filter(status__in=['approved', 'applied'])
        if not active_dn.exists():
            raise ValidationError(
                "PEMBAYARAN DIBLOKIR: Barang masuk memiliki selisih kuantitas (Qty_Actual < Qty_Ordered). "
                "Accounting WAJIB menerbitkan Nota Debit (Debit Note) terlebih dahulu sebelum pembayaran dapat diproses."
            )
