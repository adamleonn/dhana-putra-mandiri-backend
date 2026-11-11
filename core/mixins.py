from rest_framework import serializers


class RoleFilteredSerializerMixin:
    """
    Enforces strict Role-Based field masking at API representation layer:
    - Gudang: all monetary and cost fields are completely stripped from responses.
    - Sales / Admin: HPP (Cost of Goods Sold), profit margin, and stock valuation fields are stripped.
    """

    GUDANG_MONETARY_FIELDS = {
        'selling_price', 'moving_average_hpp', 'stock_value',
        'purchase_price', 'allocated_transport_cost', 'allocated_unloading_cost',
        'effective_unit_cost', 'transport_cost', 'unloading_cost',
        'payable_amount', 'debit_note_total', 'paid_amount',
        'line_total', 'unit_price', 'subtotal', 'discount_amount',
        'total_amount', 'amount', 'hpp_at_delivery', 'total_cogs',
        'base_salary', 'standard_allowance', 'allowances', 'deductions',
        'net_salary', 'previous_salary', 'new_salary', 'hourly_rate'
    }

    RESTRICTED_HPP_FIELDS = {
        'moving_average_hpp', 'stock_value', 'hpp_at_delivery',
        'total_cogs', 'effective_unit_cost'
    }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ret

        user = request.user
        if user.is_superuser or user.groups.filter(name='Direktur').exists():
            return ret

        is_gudang = user.groups.filter(name='Gudang').exists()
        is_sales = user.groups.filter(name='Sales').exists()
        is_admin = user.groups.filter(name='Admin').exists()

        if is_gudang:
            for field in self.GUDANG_MONETARY_FIELDS:
                ret.pop(field, None)
        elif is_sales or is_admin:
            for field in self.RESTRICTED_HPP_FIELDS:
                ret.pop(field, None)

        return ret

