from rest_framework import serializers
from core.models import Customer, Supplier, AuditLog


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id',
            'code',
            'name',
            'tax_id',
            'contact_person',
            'phone',
            'email',
            'address',
            'credit_limit',
            'payment_term_days',
            'is_active',
            'created_at',
            'updated_at',
        ]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id',
            'code',
            'name',
            'tax_id',
            'contact_person',
            'phone',
            'email',
            'address',
            'payment_term_days',
            'is_active',
            'created_at',
            'updated_at',
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'actor',
            'actor_username',
            'action',
            'model_name',
            'object_id',
            'object_repr',
            'changes',
            'ip_address',
            'request_id',
            'created_at',
        ]
        read_only_fields = fields

