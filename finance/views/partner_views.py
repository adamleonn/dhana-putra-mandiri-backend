from rest_framework import viewsets, permissions
from core.models import Customer, Supplier
from core.serializers import CustomerSerializer, SupplierSerializer
from core.permissions import IsStakeholderReadOnly


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
