from rest_framework import viewsets, permissions
from config.permissions import StrictRoleBasedAccess
from finance.models import SalesInvoice
from finance.serializers import SalesInvoiceSerializer


class SalesInvoiceViewSet(viewsets.ModelViewSet):
    queryset = SalesInvoice.objects.all().select_related('customer', 'delivery', 'created_by').prefetch_related('items__product')
    serializer_class = SalesInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]
