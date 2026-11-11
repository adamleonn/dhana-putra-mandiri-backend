from datetime import date
from django.db import transaction
from core.models import DocumentSequenceCounter


FORMAT_TEMPLATES = {
    'SJ': 'SJ-{period}-{number:04d}',
    'INV': 'INV/{period}/{number:04d}',
    'GR': 'GR/{period}/{number:04d}',
    'PO': 'PO/{period}/{number:04d}',
    'BKM': 'BKM/{period}/{number:04d}',
    'BKK': 'BKK/{period}/{number:04d}',
    'ND': 'ND/{period}/{number:04d}',
    'JV': 'JV/{period}/{number:04d}',
    'SLIP': 'SLIP/{period}/{number:04d}',
}


def next_number(doc_type: str, document_date: date = None) -> str:
    """
    Generate sequential gap-tolerant document numbers atomically with row-level locking.
    Uses select_for_update() to prevent race conditions during high concurrent traffic.
    """
    if document_date is None:
        document_date = date.today()

    period_key = document_date.strftime('%Y%m')

    with transaction.atomic():
        counter, _ = DocumentSequenceCounter.objects.select_for_update().get_or_create(
            doc_type=doc_type.upper(),
            period_key=period_key,
            defaults={'last_number': 0}
        )
        counter.last_number += 1
        counter.save(update_fields=['last_number', 'updated_at'])
        new_number = counter.last_number

    template = FORMAT_TEMPLATES.get(doc_type.upper(), '{doc_type}/{period}/{number:04d}')
    return template.format(
        doc_type=doc_type.upper(),
        period=period_key,
        number=new_number
    )

