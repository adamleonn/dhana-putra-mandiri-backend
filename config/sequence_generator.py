from datetime import date
from core.services.sequence_service import get_next_sequence_number


def generate_document_number(doc_type: str, date: date = None) -> str:
    return get_next_sequence_number(doc_type=doc_type, doc_date=date)
