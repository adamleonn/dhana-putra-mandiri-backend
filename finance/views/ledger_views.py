from rest_framework import viewsets, permissions
from config.permissions import IsAccountingStaff, IsFinanceKasir, IsDirekturOrSuperuser
from finance.models import GeneralLedger
from finance.serializers import GeneralLedgerSerializer


class GeneralLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeneralLedger.objects.all().select_related('period', 'created_by', 'posted_by').prefetch_related('lines__account')
    serializer_class = GeneralLedgerSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccountingStaff | IsFinanceKasir | IsDirekturOrSuperuser)]
