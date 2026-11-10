from datetime import date
from django.db import transaction
from django.utils import timezone
from core.models import DocumentSequenceCounter


@transaction.atomic
def get_next_sequence_number(doc_type: str, doc_date: date = None) -> str:
    if doc_date is None:
        doc_date = timezone.now().date()
    elif hasattr(doc_date, 'date'):
        doc_date = doc_date.date()

    period_key = doc_date.strftime('%Y%m')

    counter, _ = DocumentSequenceCounter.objects.select_for_update().get_or_create(
        doc_type=doc_type.upper(),
        period_key=period_key,
        defaults={'last_number': 0}
    )

    counter.last_number += 1
    counter.save(update_fields=['last_number', 'updated_at'])

    return f"{doc_type.upper()}/{period_key}/{counter.last_number:04d}"

