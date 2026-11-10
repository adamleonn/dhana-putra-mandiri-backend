from decimal import Decimal
from typing import Dict, Any
from django.db.models import Sum
from django.utils import timezone
from finance.models import GeneralLedgerLine
from .sales_reports import generate_sales_trends, generate_product_sales_report


def generate_annual_report(year=None) -> Dict[str, Any]:
    """
    LAPORAN TAHUNAN (ANNUAL PERFORMANCE & FINANCIAL SUMMARY)
    Menyajikan rangkuman performa fiskal 1 tahun penuh.
    """
    if year is None:
        year = timezone.now().year

    monthly_trends = generate_sales_trends(year)
    product_report = generate_product_sales_report(year)

    gl_lines = GeneralLedgerLine.objects.filter(
        ledger_entry__transaction_date__year=year,
        ledger_entry__is_posted=True
    )

    unloading_expense = gl_lines.filter(account__code='6100').aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
    payroll_expense = gl_lines.filter(account__code='6200').aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
    transport_armada = gl_lines.filter(account__code='6300').aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
    general_expense = gl_lines.filter(account__code='6400').aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')

    total_operating_expense = unloading_expense + payroll_expense + transport_armada + general_expense
    total_sales = product_report['total_revenue']
    total_cogs = product_report['total_cogs']
    gross_profit = total_sales - total_cogs
    net_operating_profit = gross_profit - total_operating_expense

    return {
        'year': year,
        'summary': {
            'total_revenue': total_sales,
            'total_cogs': total_cogs,
            'gross_profit': gross_profit,
            'operating_expenses': {
                'kuli_bongkar_expense': unloading_expense,
                'payroll_expense': payroll_expense,
                'armada_transport_expense': transport_armada,
                'office_general_expense': general_expense,
                'total': total_operating_expense,
            },
            'net_operating_profit': net_operating_profit,
            'net_profit_margin_pct': round(float((net_operating_profit / total_sales * 100)), 2) if total_sales > 0 else 0.0,
        },
        'monthly_breakdown': monthly_trends,
        'top_products': product_report['products'][:5]
    }

