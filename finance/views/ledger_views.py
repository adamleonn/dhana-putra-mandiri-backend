from rest_framework import viewsets, permissions
from core.permissions import IsAccounting, IsDirektur, IsStakeholderReadOnly
from finance.models import GeneralLedger
from finance.serializers import GeneralLedgerSerializer


class GeneralLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeneralLedger.objects.all().select_related(
        'period', 'posted_by', 'reversal_of'
    ).prefetch_related('lines__account')
    serializer_class = GeneralLedgerSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccounting | IsDirektur | IsStakeholderReadOnly)]
    filterset_fields = ['period', 'reference_type', 'date', 'is_posted']
    search_fields = ['transaction_number', 'reference_id', 'description']
