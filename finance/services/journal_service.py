from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from finance.models import ChartOfAccounts, AccountingPeriod, GeneralLedger, GeneralLedgerLine


def get_coa(code: str) -> ChartOfAccounts:
    """Retrieves ChartOfAccounts by code or raises ValidationError."""
    try:
        return ChartOfAccounts.objects.get(code=code, is_active=True)
    except ChartOfAccounts.DoesNotExist:
        raise ValidationError(f"Chart of Account '{code}' not found or is inactive.")


def validate_period_not_closed(transaction_date):
    """Ensures the accounting period containing transaction_date is not closed."""
    period = AccountingPeriod.objects.filter(
        start_date__lte=transaction_date,
        end_date__gte=transaction_date
    ).first()
    if period and period.is_closed:
        raise ValidationError(
            f"Cannot post journal: Accounting Period '{period.period_name}' is CLOSED. "
            "Only Direktur can re-open closed periods."
        )
    return period


@transaction.atomic
def create_journal_entry(
    entry_number: str,
    transaction_date,
    reference_type: str,
    reference_id: str,
    description: str,
    lines: List[Dict[str, Any]],
    posted_by=None
) -> GeneralLedger:
    """
    Creates an atomic, balanced Double-Entry Journal voucher in GeneralLedger.
    """
    validate_period_not_closed(transaction_date)
    period = AccountingPeriod.objects.filter(
        start_date__lte=transaction_date,
        end_date__gte=transaction_date
    ).first()

    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')
    resolved_lines = []

    for idx, line in enumerate(lines, start=1):
        account = get_coa(line['account_code'])
        debit = Decimal(str(line.get('debit', '0.00')))
        credit = Decimal(str(line.get('credit', '0.00')))

        if debit < Decimal('0.00') or credit < Decimal('0.00'):
            raise ValidationError(f"Line {idx}: Negative debit or credit amounts are forbidden.")
        if debit > Decimal('0.00') and credit > Decimal('0.00'):
            raise ValidationError(f"Line {idx}: A single journal line cannot have both Debit and Credit.")
        if debit == Decimal('0.00') and credit == Decimal('0.00'):
            raise ValidationError(f"Line {idx}: Journal line cannot have 0.00 for both Debit and Credit.")

        total_debit += debit
        total_credit += credit
        resolved_lines.append({
            'account': account,
            'debit': debit,
            'credit': credit,
            'memo': line.get('memo', '')
        })

    if total_debit != total_credit:
        raise ValidationError(
            f"Unbalanced Journal! Total Debit ({total_debit}) must equal Total Credit ({total_credit})."
        )

    ledger_entry = GeneralLedger.objects.create(
        entry_number=entry_number,
        transaction_date=transaction_date,
        period=period,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        is_posted=True,
        posted_by=posted_by
    )

    for item in resolved_lines:
        GeneralLedgerLine.objects.create(
            ledger_entry=ledger_entry,
            account=item['account'],
            debit=item['debit'],
            credit=item['credit'],
            memo=item['memo']
        )

    return ledger_entry

