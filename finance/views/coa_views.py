from rest_framework import viewsets, permissions
from core.permissions import DEFAULT_PERMISSIONS, MANAGEMENT, DIREKTUR_ONLY
from finance.models import ChartOfAccounts
from finance.serializers import ChartOfAccountsSerializer


class ChartOfAccountsViewSet(viewsets.ModelViewSet):
    queryset = ChartOfAccounts.objects.all().select_related('parent')
    serializer_class = ChartOfAccountsSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': MANAGEMENT, 'write': DIREKTUR_ONLY}
    filterset_fields = ['account_type', 'report_group', 'is_cash_bank', 'is_postable', 'is_active']
    search_fields = ['account_code', 'name']

