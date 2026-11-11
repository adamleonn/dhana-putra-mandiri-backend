from decimal import Decimal
from typing import Optional
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from finance.models import DebitNote
from finance.services.journal_service import create_journal_entry, get_open_period
from core.services.sequence import next_number
from core.services.audit import log_audit


@transaction.atomic
def issue_supplier_debit_note(
    goods_receipt,
    amount: Decimal,
    reason: str,
    issued_by,
    issue_date: Optional[date] = None
) -> DebitNote:
    """
    Menerbitkan Nota Debit (Debit Note) atas klaim kekurangan fisik barang masuk:
    1. Memvalidasi bahwa nominal klaim tidak melebihi total nilai kekurangan (shortage_qty * purchase_price).
    2. Memastikan periode akuntansi terbuka.
    3. Menerbitkan nomor dokumen ND otomatis melalui sequence generator.
    4. Membukukan jurnal: Dr Hutang Dagang (2110) / Cr Persediaan (1140).
    5. Menambah akumulasi debit_note_total pada GoodsReceipt sehingga membuka blokir pembayaran hutang bersih.
    6. Mencatat audit log.
    """
    if issue_date is None:
        issue_date = timezone.now().date()

    period = get_open_period(issue_date)

    # Validasi shortage amount
    items = goods_receipt.items.all()
    max_claim_amount = Decimal('0.00')
    for item in items:
        if item.qty_actual < item.qty_ordered:
            shortage = item.qty_ordered - item.qty_actual
            max_claim_amount += (shortage * item.purchase_price)

    if amount > max_claim_amount:
        raise ValidationError(
            f"Nominal Nota Debit (Rp {amount:,.2f}) melebihi batas maksimal nilai klaim kekurangan barang (Rp {max_claim_amount:,.2f})."
        )

    debit_note_number = next_number('ND', issue_date)

    journal = create_journal_entry(
        transaction_date=issue_date,
        reference_type='DEBIT_NOTE',
        reference_id=debit_note_number,
        description=f"Nota Debit #{debit_note_number} atas selisih BPB {goods_receipt.receipt_number}: {reason}",
        lines=[
            {
                'account_code': '2110',
                'debit': amount,
                'credit': Decimal('0.00'),
                'memo': f"Reduksi Hutang Supplier {goods_receipt.supplier.name}"
            },
            {
                'account_code': '1140',
                'debit': Decimal('0.00'),
                'credit': amount,
                'memo': f"Koreksi Persediaan kekurangan fisik BPB {goods_receipt.receipt_number}"
            }
        ],
        posted_by=issued_by
    )

    debit_note = DebitNote.objects.create(
        debit_note_number=debit_note_number,
        goods_receipt=goods_receipt,
        supplier=goods_receipt.supplier,
        supplier_name_snapshot=goods_receipt.supplier.name,
        date=issue_date,
        amount=amount,
        reason=reason,
        status='applied',
        journal_entry=journal,
        period=period,
        issued_by=issued_by,
        created_by=issued_by
    )

    goods_receipt.debit_note_total += amount
    goods_receipt.save(update_fields=['debit_note_total', 'updated_at'])

    log_audit(
        actor=issued_by,
        action='CREATE',
        instance=debit_note,
        changes={
            'amount': str(amount),
            'goods_receipt': goods_receipt.receipt_number,
            'status': 'applied'
        }
    )

    return debit_note
