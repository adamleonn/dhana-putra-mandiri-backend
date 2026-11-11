from rest_framework import viewsets, permissions
from core.permissions import IsAccounting, IsDirektur, IsStakeholderReadOnly
from finance.models import ChartOfAccounts
from finance.serializers import ChartOfAccountsSerializer


class ChartOfAccountsViewSet(viewsets.ModelViewSet):
    queryset = ChartOfAccounts.objects.all().select_related('parent')
    serializer_class = ChartOfAccountsSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['account_type', 'report_group', 'is_cash_bank', 'is_postable', 'is_active']
    search_fields = ['account_code', 'name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAccounting() | IsDirektur())]
        return super().get_permissions()
