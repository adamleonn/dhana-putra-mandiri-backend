from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from finance.models import SalesInvoice, SalesInvoiceRevision
from core.services.audit import log_audit


@transaction.atomic
def revise_sales_invoice_shortage(
    invoice: SalesInvoice,
    new_subtotal: Decimal,
    reason: str,
    revised_by
) -> SalesInvoiceRevision:
    """
    Accounting only: Melakukan revisi nilai Faktur Penjualan atas selisih barang kirim.
    Mencatat histori revisi secara transparan dan ter-audit pada SalesInvoiceRevision.
    """
    if invoice.status == 'cancelled':
        raise ValidationError("Faktur yang telah dibatalkan tidak dapat direvisi.")

    old_total = invoice.total_amount
    new_total = max(Decimal('0.00'), new_subtotal - invoice.discount_amount)

    invoice.revision_no += 1
    invoice.subtotal = new_subtotal
    invoice.total_amount = new_total
    invoice.save(update_fields=['revision_no', 'subtotal', 'total_amount', 'updated_at'])

    revision = SalesInvoiceRevision.objects.create(
        invoice=invoice,
        revised_by=revised_by,
        revision_number=invoice.revision_no,
        old_total=old_total,
        new_total=new_total,
        reason=reason
    )

    log_audit(
        actor=revised_by,
        action='UPDATE',
        instance=invoice,
        changes={
            'revision_number': invoice.revision_no,
            'old_total': str(old_total),
            'new_total': str(new_total),
            'reason': reason
        }
    )

    return revision

