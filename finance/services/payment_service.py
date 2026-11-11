from decimal import Decimal
from typing import Optional
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from finance.models import Payment, SalesInvoice, ChartOfAccounts
from inventory.models import GoodsReceipt
from finance.services.journal_service import create_journal_entry, reverse_journal_entry, get_open_period
from core.services.sequence import next_number
from core.services.audit import log_audit


@transaction.atomic
def process_customer_receipt(
    sales_invoice: SalesInvoice,
    cash_bank_account: ChartOfAccounts,
    amount: Decimal,
    payment_date: date,
    payment_method: str,
    actor,
    reference_number: str = '',
    notes: str = ''
) -> Payment:
    """
    Memproses pelunasan piutang pelanggan (BKM - Bukti Kas Masuk):
    1. Validasi akun adalah Kas atau Bank (is_cash_bank=True).
    2. Validasi periode akuntansi aktif.
    3. Mengunci baris Faktur dengan select_for_update().
    4. Validasi nominal tidak melebihi sisa piutang.
    5. Jurnal: Dr Kas/Bank / Cr Piutang Dagang (1130).
    6. Update paid_amount & status faktur (partially_paid / paid).
    """
    if not cash_bank_account.is_cash_bank:
        raise ValidationError(f"Akun '{cash_bank_account.name}' bukan merupakan akun Kas atau Bank.")

    get_open_period(payment_date)

    invoice = SalesInvoice.objects.select_for_update().get(pk=sales_invoice.pk)
    if invoice.status == 'cancelled':
        raise ValidationError(f"Faktur {invoice.invoice_number} telah dibatalkan.")

    remaining = invoice.remaining_due
    if amount > remaining:
        raise ValidationError(
            f"Nominal pembayaran (Rp {amount:,.2f}) melebihi sisa tagihan piutang (Rp {remaining:,.2f})."
        )

    bkm_number = next_number('BKM', payment_date)

    journal = create_journal_entry(
        transaction_date=payment_date,
        reference_type='PAYMENT_BKM',
        reference_id=bkm_number,
        description=f"Penerimaan Piutang Faktur {invoice.invoice_number} dari {invoice.customer.name}",
        lines=[
            {
                'account_code': cash_bank_account.account_code,
                'debit': amount,
                'credit': Decimal('0.00'),
                'memo': f"Kas/Bank Masuk Pelunasan Faktur {invoice.invoice_number}"
            },
            {
                'account_code': '1130',
                'debit': Decimal('0.00'),
                'credit': amount,
                'memo': f"Pengurangan Piutang Dagang {invoice.customer.name}"
            }
        ],
        posted_by=actor
    )

    payment = Payment.objects.create(
        payment_number=bkm_number,
        payment_method=payment_method,
        category='customer_receipt',
        direction='IN',
        cash_bank_account=cash_bank_account,
        sales_invoice=invoice,
        amount=amount,
        payment_date=payment_date,
        reference_number=reference_number,
        status='completed',
        notes=notes,
        journal_entry=journal,
        created_by=actor
    )

    invoice.paid_amount += amount
    if invoice.paid_amount >= invoice.total_amount:
        invoice.status = 'paid'
    else:
        invoice.status = 'partially_paid'
    invoice.save(update_fields=['paid_amount', 'status', 'updated_at'])

    log_audit(
        actor=actor,
        action='CONFIRM',
        instance=payment,
        changes={
            'amount': str(amount),
            'invoice_number': invoice.invoice_number,
            'invoice_status': invoice.status
        }
    )

    return payment


@transaction.atomic
def process_supplier_payment(
    goods_receipt: GoodsReceipt,
    cash_bank_account: ChartOfAccounts,
    amount: Decimal,
    payment_date: date,
    payment_method: str,
    actor,
    reference_number: str = '',
    notes: str = ''
) -> Payment:
    """
    Memproses pembayaran hutang dagang ke supplier (BKK - Bukti Kas Keluar):
    1. Shortage Control: Jika ada selisih kurang fisik (Qty Actual < Qty Ordered),
       pembayaran DIBLOKIR hingga Nota Debit diterbitkan.
    2. Validasi nominal <= net_payable - paid_amount.
    3. Jurnal: Dr Hutang Dagang (2110) / Cr Kas/Bank.
    4. Update status pembayaran BPB (partial / paid).
    """
    if not cash_bank_account.is_cash_bank:
        raise ValidationError(f"Akun '{cash_bank_account.name}' bukan merupakan akun Kas atau Bank.")

    get_open_period(payment_date)

    receipt = GoodsReceipt.objects.select_for_update().get(pk=goods_receipt.pk)

    # Shortage Control Gate
    if receipt.has_quantity_discrepancy and receipt.debit_note_total == Decimal('0.00'):
        raise ValidationError(
            "PEMBAYARAN DIBLOKIR: Barang masuk memiliki selisih kuantitas fisik (Qty Actual < Qty Ordered). "
            "Bagian Accounting WAJIB menerbitkan Nota Debit (Debit Note) terlebih dahulu sebelum pembayaran dapat dicairkan."
        )

    net_payable = receipt.net_payable
    max_payable = net_payable - receipt.paid_amount
    if amount > max_payable:
        raise ValidationError(
            f"Nominal pembayaran (Rp {amount:,.2f}) melebihi sisa hutang bersih supplier (Rp {max_payable:,.2f})."
        )

    bkk_number = next_number('BKK', payment_date)

    journal = create_journal_entry(
        transaction_date=payment_date,
        reference_type='PAYMENT_BKK',
        reference_id=bkk_number,
        description=f"Pembayaran Hutang Supplier BPB {receipt.receipt_number} kepada {receipt.supplier.name}",
        lines=[
            {
                'account_code': '2110',
                'debit': amount,
                'credit': Decimal('0.00'),
                'memo': f"Pelunasan Hutang Dagang {receipt.supplier.name}"
            },
            {
                'account_code': cash_bank_account.account_code,
                'debit': Decimal('0.00'),
                'credit': amount,
                'memo': f"Kas/Bank Keluar Pembayaran BPB {receipt.receipt_number}"
            }
        ],
        posted_by=actor
    )

    payment = Payment.objects.create(
        payment_number=bkk_number,
        payment_method=payment_method,
        category='supplier_payment',
        direction='OUT',
        cash_bank_account=cash_bank_account,
        goods_receipt=receipt,
        amount=amount,
        payment_date=payment_date,
        reference_number=reference_number,
        status='completed',
        notes=notes,
        journal_entry=journal,
        created_by=actor
    )

    receipt.paid_amount += amount
    if receipt.paid_amount >= net_payable:
        receipt.payment_status = 'paid'
    else:
        receipt.payment_status = 'partial'
    receipt.save(update_fields=['paid_amount', 'payment_status', 'updated_at'])

    log_audit(
        actor=actor,
        action='CONFIRM',
        instance=payment,
        changes={
            'amount': str(amount),
            'receipt_number': receipt.receipt_number,
            'payment_status': receipt.payment_status
        }
    )

    return payment


@transaction.atomic
def process_payroll_payment(
    payroll_slip,
    cash_bank_account: ChartOfAccounts,
    payment_date: date,
    payment_method: str,
    actor,
    reference_number: str = '',
    notes: str = ''
) -> Payment:
    """
    Pencairan kas/bank untuk pembayaran gaji karyawan yang telah disetujui (Approved):
    Jurnal: Dr Hutang Beban Gaji (2120) / Cr Kas/Bank.
    """
    if not cash_bank_account.is_cash_bank:
        raise ValidationError(f"Akun '{cash_bank_account.name}' bukan merupakan akun Kas atau Bank.")

    get_open_period(payment_date)

    if payroll_slip.status != 'approved':
        raise ValidationError(f"Slip gaji status '{payroll_slip.status}' belum disetujui oleh Direktur.")

    bkk_number = next_number('BKK', payment_date)
    amount = payroll_slip.net_salary

    journal = create_journal_entry(
        transaction_date=payment_date,
        reference_type='PAYMENT_PAYROLL',
        reference_id=bkk_number,
        description=f"Pembayaran Gaji Karyawan {payroll_slip.employee.full_name} ({payroll_slip.slip_number})",
        lines=[
            {
                'account_code': '2120',
                'debit': amount,
                'credit': Decimal('0.00'),
                'memo': f"Pelunasan Hutang Gaji {payroll_slip.employee.full_name}"
            },
            {
                'account_code': cash_bank_account.account_code,
                'debit': Decimal('0.00'),
                'credit': amount,
                'memo': f"Kas Keluar Transfer Gaji {payroll_slip.slip_number}"
            }
        ],
        posted_by=actor
    )

    payment = Payment.objects.create(
        payment_number=bkk_number,
        payment_method=payment_method,
        category='payroll',
        direction='OUT',
        cash_bank_account=cash_bank_account,
        payroll_slip=payroll_slip,
        amount=amount,
        payment_date=payment_date,
        reference_number=reference_number,
        status='completed',
        notes=notes,
        journal_entry=journal,
        created_by=actor
    )

    payroll_slip.status = 'paid'
    payroll_slip.payment = payment
    payroll_slip.paid_by = actor
    payroll_slip.payment_date = payment_date
    payroll_slip.save(update_fields=['status', 'payment', 'paid_by', 'payment_date', 'updated_at'])

    log_audit(
        actor=actor,
        action='CONFIRM',
        instance=payment,
        changes={
            'amount': str(amount),
            'payroll_slip': payroll_slip.slip_number
        }
    )

    return payment
