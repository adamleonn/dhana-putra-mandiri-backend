from rest_framework import viewsets, permissions
from core.models import Customer, Supplier, AuditLog
from core.serializers import CustomerSerializer, SupplierSerializer, AuditLogSerializer
from core.permissions import IsStakeholderReadOnly, IsDirektur, IsAdminOps, IsSales, IsAccounting


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('code')
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'phone', 'contact_person']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('code')
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['code', 'name', 'phone', 'contact_person']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().select_related('actor').order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsDirektur | IsAccounting]
    filterset_fields = ['action', 'model_name', 'actor']
    search_fields = ['object_id', 'object_repr', 'request_id']
