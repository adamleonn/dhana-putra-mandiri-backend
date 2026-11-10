from rest_framework import viewsets, permissions
from config.permissions import StrictRoleBasedAccess
from finance.models import ChartOfAccounts
from finance.serializers import ChartOfAccountsSerializer


class ChartOfAccountsViewSet(viewsets.ModelViewSet):
    """
    Chart of Accounts (COA) ViewSet.
    Read-only for most roles; Accounting and Direktur can manage accounts.
    """
    queryset = ChartOfAccounts.objects.all()
    serializer_class = ChartOfAccountsSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

