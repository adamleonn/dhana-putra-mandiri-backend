from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from config.permissions import StrictRoleBasedAccess, CanManageAccountingPeriod, IsAccountingStaff, IsDirekturOrSuperuser
from finance.models import AccountingPeriod
from finance.serializers import AccountingPeriodSerializer


class AccountingPeriodViewSet(viewsets.ModelViewSet):
    queryset = AccountingPeriod.objects.all()
    serializer_class = AccountingPeriodSerializer
    permission_classes = [permissions.IsAuthenticated, StrictRoleBasedAccess]

    @action(detail=True, methods=['post'], permission_classes=[CanManageAccountingPeriod])
    def close_period(self, request, pk=None):
        period = self.get_object()
        if period.status == 'CLOSED':
            return Response({'error': f"Period '{period.period_name}' is already closed."}, status=status.HTTP_400_BAD_REQUEST)

        period.status = 'CLOSED'
        period.closed_by = request.user
        period.closed_at = timezone.now()
        period.save(update_fields=['status', 'closed_by', 'closed_at', 'updated_at'])

        return Response(
            {
                'message': f"Accounting Period '{period.period_name}' has been CLOSED.",
                'closed_by': request.user.get_full_name() or request.user.username,
                'closed_at': period.closed_at
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[CanManageAccountingPeriod])
    def reopen_period(self, request, pk=None):
        period = self.get_object()
        if period.status != 'CLOSED':
            return Response({'error': f"Period '{period.period_name}' is not closed."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Alasan pembukaan kembali periode wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)

        period.status = 'OPEN'
        period.reopened_by = request.user
        period.reopened_at = timezone.now()
        period.reopen_reason = reason
        period.save(update_fields=['status', 'reopened_by', 'reopened_at', 'reopen_reason', 'updated_at'])

        return Response(
            {
                'message': f"Accounting Period '{period.period_name}' has been REOPENED.",
                'reopened_by': request.user.get_full_name() or request.user.username,
                'reopened_at': period.reopened_at,
                'reason': reason
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAccountingStaff | IsDirekturOrSuperuser])
    def submit_period(self, request, pk=None):
        period = self.get_object()
        if period.status != 'OPEN':
            return Response({'error': f"Only OPEN periods can be submitted. Current status: '{period.status}'."}, status=status.HTTP_400_BAD_REQUEST)

        period.status = 'SUBMITTED'
        period.save(update_fields=['status', 'updated_at'])

        return Response(
            {
                'message': f"Accounting Period '{period.period_name}' has been SUBMITTED for closing review.",
                'status': period.status
            },
            status=status.HTTP_200_OK
        )
