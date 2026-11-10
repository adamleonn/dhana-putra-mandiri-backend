from decimal import Decimal
from typing import Dict, Any, List
from django.db.models import Sum
from django.utils import timezone
from finance.models import SalesInvoice, SalesInvoiceItem


def generate_product_sales_report(year=None) -> Dict[str, Any]:
    """
    LAPORAN PENJUALAN PER PRODUK & MARGIN LABA:
    Menghitung volume penjualan, pendapatan kotor, HPP, laba kotor, dan % margin laba per SKU.
    """
    if year is None:
        year = timezone.now().year

    items = SalesInvoiceItem.objects.filter(
        invoice__invoice_date__year=year,
        invoice__status__in=['unpaid', 'partially_paid', 'paid']
    ).select_related('product')

    product_stats = {}
    for line in items:
        p = line.product
        if p.id not in product_stats:
            product_stats[p.id] = {
                'sku': p.sku,
                'name': p.name,
                'brand': getattr(p, 'brand', 'Lainnya'),
                'package_size': getattr(p, 'package_size', '2L'),
                'uom': p.uom,
                'current_stock': p.current_stock,
                'moving_average_hpp': p.moving_average_hpp,
                'selling_price': p.selling_price,
                'qty_sold': Decimal('0.00'),
                'revenue': Decimal('0.00'),
                'cogs': Decimal('0.00'),
            }

        line_revenue = line.line_total
        line_cogs = line.qty * p.moving_average_hpp

        product_stats[p.id]['qty_sold'] += line.qty
        product_stats[p.id]['revenue'] += line_revenue
        product_stats[p.id]['cogs'] += line_cogs

    results = []
    total_revenue_all = Decimal('0.00')
    total_cogs_all = Decimal('0.00')

    for p_id, data in product_stats.items():
        gross_profit = data['revenue'] - data['cogs']
        margin_pct = (gross_profit / data['revenue'] * Decimal('100.00')) if data['revenue'] > 0 else Decimal('0.00')
        data['gross_profit'] = gross_profit
        data['margin_percentage'] = round(float(margin_pct), 2)
        total_revenue_all += data['revenue']
        total_cogs_all += data['cogs']
        results.append(data)

    results.sort(key=lambda x: x['revenue'], reverse=True)

    return {
        'year': year,
        'total_revenue': total_revenue_all,
        'total_cogs': total_cogs_all,
        'total_gross_profit': total_revenue_all - total_cogs_all,
        'products': results
    }


def generate_sales_trends(year=None) -> List[Dict[str, Any]]:
    """
    GRAFIK TREN PENJUALAN BULANAN (12 Bulan):
    Menyajikan time-series omset, volume karton, HPP, dan laba kotor per bulan.
    """
    if year is None:
        year = timezone.now().year

    trends = []
    month_names = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ]

    for m in range(1, 13):
        invoices = SalesInvoice.objects.filter(
            invoice_date__year=year,
            invoice_date__month=m,
            status__in=['unpaid', 'partially_paid', 'paid']
        )
        total_sales = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        items = SalesInvoiceItem.objects.filter(
            invoice__in=invoices
        ).select_related('product')
        total_qty = items.aggregate(Sum('qty'))['qty__sum'] or Decimal('0.00')

        cogs = sum((item.qty * item.product.moving_average_hpp for item in items), Decimal('0.00'))
        gross_profit = total_sales - cogs

        trends.append({
            'month': m,
            'month_name': month_names[m - 1],
            'period': f"{year}-{m:02d}",
            'total_sales': total_sales,
            'total_volume': total_qty,
            'total_cogs': cogs,
            'gross_profit': gross_profit
        })

    return trends

