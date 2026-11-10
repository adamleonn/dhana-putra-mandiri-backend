from decimal import Decimal
from typing import Dict, List, Any
from inventory.models import Product


def calculate_abc_classification() -> Dict[str, List[Dict[str, Any]]]:
    products = list(Product.objects.filter(is_active=True))
    if not products:
        return {'A': [], 'B': [], 'C': []}

    product_values = []
    total_portfolio_value = Decimal('0.00')

    for p in products:
        val = (p.current_stock * p.moving_average_hpp).quantize(Decimal('0.01'))
        product_values.append({'product': p, 'value': val})
        total_portfolio_value += val

    product_values.sort(key=lambda x: x['value'], reverse=True)

    cumulative = Decimal('0.00')
    classified = {'A': [], 'B': [], 'C': []}

    for item in product_values:
        p = item['product']
        val = item['value']
        if total_portfolio_value > Decimal('0.00'):
            percentage = (val / total_portfolio_value) * Decimal('100.00')
            cumulative += percentage
        else:
            percentage = Decimal('0.00')
            cumulative = Decimal('0.00')

        if cumulative <= Decimal('80.00'):
            new_class = 'A'
        elif cumulative <= Decimal('95.00'):
            new_class = 'B'
        else:
            new_class = 'C'

        p.abc_class = new_class
        p.save(update_fields=['abc_class'])

        classified[new_class].append({
            'sku': p.sku,
            'name': p.name,
            'current_stock': p.current_stock,
            'moving_average_hpp': p.moving_average_hpp,
            'total_value': val,
            'percentage': round(float(percentage), 2),
            'cumulative_percentage': round(float(cumulative), 2),
            'abc_class': new_class,
            'estimated_runway_days': p.estimated_stock_days,
            'is_stock_below_28_days': p.is_stock_below_28_days
        })

    return classified
