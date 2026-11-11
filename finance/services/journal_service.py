from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from finance.models import ChartOfAccounts, AccountingPeriod, GeneralLedger, GeneralLedgerLine
from config.exceptions import PeriodClosedError, DuplicatePostingError
from core.services.sequence import next_number
from core.services.audit import log_audit


def get_coa(account_code: str) -> ChartOfAccounts:
    """Retrieves ChartOfAccounts by account_code or raises ValidationError."""
    try:
        return ChartOfAccounts.objects.get(account_code=account_code, is_active=True)
    except ChartOfAccounts.DoesNotExist:
        raise ValidationError(f"Akun Chart of Accounts '{account_code}' tidak ditemukan atau tidak aktif.")


def get_open_period(transaction_date: date) -> AccountingPeriod:
    """
    Ensures an accounting period exists for transaction_date and is strictly OPEN.
    Raises PeriodClosedError if period is CLOSED or SUBMITTED.
    """
    period = AccountingPeriod.objects.filter(
        start_date__lte=transaction_date,
        end_date__gte=transaction_date
    ).first()

    if not period:
        raise ValidationError(f"Tidak ada Periode Akuntansi yang mencakup tanggal {transaction_date}.")

    if period.status != 'OPEN':
        raise PeriodClosedError(
            f"Transaksi ditolak: Periode Akuntansi '{period.period_name}' berstatus {period.status}. "
            "Hanya Direktur yang berwenang membuka kembali periode.",
            period_name=period.period_name
        )

    return period


@transaction.atomic
def create_journal_entry(
    transaction_date: date,
    reference_type: str,
    reference_id: str,
    description: str,
    lines: List[Dict[str, Any]],
    posted_by,
    reversal_of: Optional[GeneralLedger] = None
) -> GeneralLedger:
    """
    Creates an atomic, strictly balanced Double-Entry Journal voucher in GeneralLedger.
    Idempotent: prevents duplicate postings for the same reference unless it is a reversal.
    """
    period = get_open_period(transaction_date)

    if not reversal_of:
        existing = GeneralLedger.objects.filter(
            reference_type=reference_type,
            reference_id=reference_id,
            reversal_of__isnull=True
        ).first()
        if existing:
            raise DuplicatePostingError(
                f"Jurnal untuk referensi {reference_type}#{reference_id} sudah pernah dibukukan ({existing.transaction_number}).",
                reference=f"{reference_type}#{reference_id}"
            )

    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')
    resolved_lines = []

    for idx, line in enumerate(lines, start=1):
        account = get_coa(line['account_code'])
        if not account.is_postable:
            raise ValidationError(f"Baris {idx}: Akun {account.account_code} bukan akun postable (detail).")

        debit = Decimal(str(line.get('debit', '0.00'))).quantize(Decimal('0.01'))
        credit = Decimal(str(line.get('credit', '0.00'))).quantize(Decimal('0.01'))

        if debit < Decimal('0.00') or credit < Decimal('0.00'):
            raise ValidationError(f"Baris {idx}: Nominal debit atau kredit tidak boleh negatif.")
        if debit > Decimal('0.00') and credit > Decimal('0.00'):
            raise ValidationError(f"Baris {idx}: Satu baris jurnal tidak boleh memiliki Debit dan Kredit sekaligus.")
        if debit == Decimal('0.00') and credit == Decimal('0.00'):
            raise ValidationError(f"Baris {idx}: Nilai debit dan kredit tidak boleh keduanya nol.")

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
            f"Jurnal tidak seimbang (Unbalanced)! Total Debit (Rp {total_debit:,.2f}) harus sama dengan Total Kredit (Rp {total_credit:,.2f})."
        )

    transaction_number = next_number('JV', transaction_date)

    ledger_entry = GeneralLedger.objects.create(
        transaction_number=transaction_number,
        period=period,
        date=transaction_date,
        reference_type=reference_type,
        reference_id=str(reference_id),
        description=description,
        is_posted=True,
        reversal_of=reversal_of,
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

    log_audit(
        actor=posted_by,
        action='CREATE',
        instance=ledger_entry,
        changes={
            'transaction_number': transaction_number,
            'total_debit': str(total_debit),
            'total_credit': str(total_credit),
            'reference': f"{reference_type}#{reference_id}"
        }
    )

    return ledger_entry


@transaction.atomic
def reverse_journal_entry(
    original_entry: GeneralLedger,
    reversal_date: date,
    reason: str,
    posted_by
) -> GeneralLedger:
    """
    Creates an exact reversing journal entry (swapping Debits and Credits).
    """
    reversal_lines = []
    for line in original_entry.lines.all():
        reversal_lines.append({
            'account_code': line.account.account_code,
            'debit': line.credit,
            'credit': line.debit,
            'memo': f"Reversal: {line.memo or original_entry.description}"
        })

    return create_journal_entry(
        transaction_date=reversal_date,
        reference_type=f"REV_{original_entry.reference_type}",
        reference_id=original_entry.reference_id,
        description=f"Pembalik Jurnal {original_entry.transaction_number}: {reason}",
        lines=reversal_lines,
        posted_by=posted_by,
        reversal_of=original_entry
    )
