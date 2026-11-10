from decimal import Decimal
from typing import Optional
from django.db import transaction
from django.utils import timezone
from finance.models import DebitNote
from .journal_service import create_journal_entry
from config.sequence_generator import generate_document_number


@transaction.atomic
def issue_supplier_debit_note(
    goods_receipt,
    amount: Decimal,
    reason: str,
    issued_by,
    debit_note_number: Optional[str] = None
) -> DebitNote:
    today = timezone.now().date()
    if not debit_note_number:
        debit_note_number = generate_document_number('ND', today)

    entry_number = generate_document_number('JV', today)

    journal = create_journal_entry(
        entry_number=entry_number,
        transaction_date=today,
        reference_type='DEBIT_NOTE',
        reference_id=debit_note_number,
        description=f"Nota Debit Supplier {goods_receipt.supplier_name} atas selisih GR {goods_receipt.receipt_number}: {reason}",
        lines=[
            {
                'account_code': '2110',
                'debit': amount,
                'credit': Decimal('0.00'),
                'memo': f"Reduksi Hutang Supplier {goods_receipt.supplier_name}"
            },
            {
                'account_code': '1140',
                'debit': Decimal('0.00'),
                'credit': amount,
                'memo': f"Koreksi Persediaan atas barang kurang kirim {goods_receipt.receipt_number}"
            }
        ],
        posted_by=issued_by
    )

    debit_note = DebitNote.objects.create(
        debit_note_number=debit_note_number,
        goods_receipt=goods_receipt,
        supplier=goods_receipt.supplier,
        supplier_name=goods_receipt.supplier_name,
        date=today,
        amount=amount,
        reason=reason,
        status='applied',
        journal_entry=journal,
        created_by=issued_by,
        issued_by=issued_by
    )

    return debit_note
