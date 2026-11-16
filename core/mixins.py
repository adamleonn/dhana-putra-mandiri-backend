from rest_framework import serializers

from core.roles import ADMIN, DIREKTUR, GUDANG, get_user_roles


class RoleFilteredSerializerMixin:
    """
    Enforces strict Role-Based field masking at API representation layer:
    - Gudang: all monetary and cost fields are completely stripped from responses.
    - Admin: HPP (Cost of Goods Sold), profit margin, and stock valuation fields are stripped.
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

        roles = get_user_roles(request.user)
        if DIREKTUR in roles:
            return ret

        if GUDANG in roles or not roles:
            for field in self.GUDANG_MONETARY_FIELDS:
                ret.pop(field, None)
        elif ADMIN in roles:
            for field in self.RESTRICTED_HPP_FIELDS:
                ret.pop(field, None)

        return ret

