from decimal import Decimal
from typing import Dict, Any
from inventory.models import Product


def generate_pie_chart_analytics() -> Dict[str, Any]:
    """
    VISUALISASI PIE CHART UNTUK SETIAP MEREK DAN UKURAN (Next.js Dashboard ready):
    1. Pie Chart Penjualan & Stok Berdasarkan Merek (Bimoli, Filma, Sania, SunCo, Minyakita, Curah, dll.)
    2. Pie Chart Penjualan & Stok Berdasarkan Ukuran Kemasan (1L, 2L, 5L, 18L, Curah)
    """
    products = Product.objects.filter(is_active=True)

    brand_stats = {}
    size_stats = {}
    total_stock_value = Decimal('0.00')

    for p in products:
        brand = p.brand or 'Lainnya'
        size = p.package_size or 'Lainnya'
        stock_val = (p.current_stock * p.moving_average_hpp).quantize(Decimal('0.01'))
        total_stock_value += stock_val

        # Brand aggregation
        if brand not in brand_stats:
            brand_stats[brand] = {'brand': brand, 'stock_qty': Decimal('0.00'), 'stock_value': Decimal('0.00')}
        brand_stats[brand]['stock_qty'] += p.current_stock
        brand_stats[brand]['stock_value'] += stock_val

        # Size aggregation
        if size not in size_stats:
            size_stats[size] = {'package_size': size, 'stock_qty': Decimal('0.00'), 'stock_value': Decimal('0.00')}
        size_stats[size]['stock_qty'] += p.current_stock
        size_stats[size]['stock_value'] += stock_val

    pie_brands = []
    for brand, val in brand_stats.items():
        pct = (val['stock_value'] / total_stock_value * 100) if total_stock_value > 0 else Decimal('0.00')
        pie_brands.append({
            'label': brand,
            'stock_value': val['stock_value'],
            'stock_qty': val['stock_qty'],
            'percentage': round(float(pct), 2)
        })

    pie_sizes = []
    for size, val in size_stats.items():
        pct = (val['stock_value'] / total_stock_value * 100) if total_stock_value > 0 else Decimal('0.00')
        pie_sizes.append({
            'label': size,
            'stock_value': val['stock_value'],
            'stock_qty': val['stock_qty'],
            'percentage': round(float(pct), 2)
        })

    pie_brands.sort(key=lambda x: x['stock_value'], reverse=True)
    pie_sizes.sort(key=lambda x: x['stock_value'], reverse=True)

    return {
        'total_portfolio_value': total_stock_value,
        'brand_distribution': pie_brands,
        'package_size_distribution': pie_sizes,
    }

