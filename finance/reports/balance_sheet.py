from decimal import Decimal
from typing import Dict, Any
from django.db.models import Sum
from django.utils import timezone
from finance.models import ChartOfAccounts, GeneralLedgerLine


def get_account_balance(account_code: str, as_of_date=None) -> Decimal:
    """Calculates cumulative net balance for an account code."""
    qs = GeneralLedgerLine.objects.filter(account__account_code=account_code, ledger_entry__is_posted=True)
    if as_of_date:
        qs = qs.filter(ledger_entry__date__lte=as_of_date)

    debit_sum = qs.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
    credit_sum = qs.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')

    account = ChartOfAccounts.objects.filter(account_code=account_code).first()
    if not account:
        return Decimal('0.00')

    if account.account_type in ['ASSET', 'EXPENSE']:
        return debit_sum - credit_sum
    else:
        return credit_sum - debit_sum


def generate_balance_sheet(as_of_date=None) -> Dict[str, Any]:
    if as_of_date is None:
        as_of_date = timezone.now().date()

    kas_tunai = get_account_balance('1110', as_of_date)
    bank_bca = get_account_balance('1120', as_of_date)
    bank_mandiri = get_account_balance('1121', as_of_date)
    piutang_usaha = get_account_balance('1130', as_of_date)
    persediaan_barang = get_account_balance('1140', as_of_date)

    total_kas_bank = kas_tunai + bank_bca + bank_mandiri
    total_aset_lancar = total_kas_bank + piutang_usaha + persediaan_barang
    total_aset = total_aset_lancar

    hutang_usaha = get_account_balance('2110', as_of_date)
    hutang_gaji = get_account_balance('2120', as_of_date)
    hutang_bongkar = get_account_balance('2130', as_of_date)
    total_kewajiban = hutang_usaha + hutang_gaji + hutang_bongkar

    pendapatan = get_account_balance('4100', as_of_date) - get_account_balance('4200', as_of_date)
    hpp = get_account_balance('5100', as_of_date)
    beban_operasional = (
        get_account_balance('6100', as_of_date)
        + get_account_balance('6110', as_of_date)
        + get_account_balance('6120', as_of_date)
        + get_account_balance('6200', as_of_date)
    )
    laba_periode_berjalan = pendapatan - hpp - beban_operasional

    modal_disetor = get_account_balance('3100', as_of_date)
    laba_ditahan = get_account_balance('3200', as_of_date)
    total_ekuitas = modal_disetor + laba_ditahan + laba_periode_berjalan

    total_kewajiban_dan_ekuitas = total_kewajiban + total_ekuitas
    is_balanced = (total_aset == total_kewajiban_dan_ekuitas)

    return {
        'as_of_date': as_of_date.isoformat(),
        'assets': {
            'kas_dan_bank': {
                'kas_tunai': kas_tunai,
                'bank_bca': bank_bca,
                'bank_mandiri': bank_mandiri,
                'subtotal': total_kas_bank,
            },
            'piutang_usaha': piutang_usaha,
            'persediaan_barang_dagang': persediaan_barang,
            'total_assets': total_aset,
        },
        'liabilities': {
            'hutang_usaha_supplier': hutang_usaha,
            'hutang_gaji_upah': hutang_gaji,
            'hutang_ongkos_bongkar': hutang_bongkar,
            'total_liabilities': total_kewajiban,
        },
        'equity': {
            'modal_disetor': modal_disetor,
            'laba_ditahan': laba_ditahan,
            'laba_periode_berjalan': laba_periode_berjalan,
            'total_equity': total_ekuitas,
        },
        'summary': {
            'total_assets': total_aset,
            'total_liabilities_and_equity': total_kewajiban_dan_ekuitas,
            'difference': total_aset - total_kewajiban_dan_ekuitas,
            'is_balanced': is_balanced,
        }
    }
