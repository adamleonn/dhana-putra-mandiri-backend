from rest_framework import viewsets, permissions
from config.permissions import StrictRoleBasedAccess
from core.models import Customer, Supplier
from finance.serializers import CustomerSerializer, SupplierSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

