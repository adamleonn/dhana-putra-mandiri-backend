from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from core.permissions import IsDirektur, IsAccounting, IsStakeholderReadOnly
from finance.models import AccountingPeriod
from finance.serializers import AccountingPeriodSerializer
from core.services.audit import log_audit


class AccountingPeriodViewSet(viewsets.ModelViewSet):
    queryset = AccountingPeriod.objects.all().select_related('closed_by', 'reopened_by', 'submitted_by')
    serializer_class = AccountingPeriodSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status']
    search_fields = ['period_name']

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsDirektur])
    def close_period(self, request, pk=None):
        period = self.get_object()
        if period.status == 'CLOSED':
            return Response({'error': f"Periode '{period.period_name}' sudah ditutup sebelumnya."}, status=status.HTTP_400_BAD_REQUEST)

        closing_notes = request.data.get('closing_notes', '')

        period.status = 'CLOSED'
        period.closed_by = request.user
        period.closed_at = timezone.now()
        period.closing_notes = closing_notes
        period.save(update_fields=['status', 'closed_by', 'closed_at', 'closing_notes', 'updated_at'])

        log_audit(
            actor=request.user,
            action='CLOSE_PERIOD',
            instance=period,
            changes={'status': 'CLOSED', 'notes': closing_notes}
        )

        return Response(
            {
                'message': f"Periode Akuntansi '{period.period_name}' telah resmi DITUTUP oleh Direktur.",
                'closed_by': request.user.username,
                'closed_at': period.closed_at
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsDirektur])
    def reopen_period(self, request, pk=None):
        period = self.get_object()
        if period.status != 'CLOSED':
            return Response({'error': f"Periode '{period.period_name}' tidak dalam status CLOSED."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Alasan pembukaan kembali periode akuntansi wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)

        period.status = 'OPEN'
        period.reopened_by = request.user
        period.reopened_at = timezone.now()
        period.reopen_reason = reason
        period.save(update_fields=['status', 'reopened_by', 'reopened_at', 'reopen_reason', 'updated_at'])

        log_audit(
            actor=request.user,
            action='REOPEN_PERIOD',
            instance=period,
            changes={'status': 'OPEN', 'reason': reason}
        )

        return Response(
            {
                'message': f"Periode Akuntansi '{period.period_name}' telah DIBUKA KEMBALI oleh Direktur.",
                'reopened_by': request.user.username,
                'reopened_at': period.reopened_at,
                'reason': reason
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsAccounting | IsDirektur])
    def submit_period(self, request, pk=None):
        period = self.get_object()
        if period.status != 'OPEN':
            return Response({'error': f"Hanya periode berstatus OPEN yang dapat diajukan tutup buku. Status saat ini: '{period.status}'."}, status=status.HTTP_400_BAD_REQUEST)

        period.status = 'SUBMITTED'
        period.submitted_by = request.user
        period.submitted_at = timezone.now()
        period.save(update_fields=['status', 'submitted_by', 'submitted_at', 'updated_at'])

        log_audit(
            actor=request.user,
            action='UPDATE',
            instance=period,
            changes={'status': 'SUBMITTED'}
        )

        return Response(
            {
                'message': f"Periode Akuntansi '{period.period_name}' telah DIAJUKAN untuk penutupan buku.",
                'status': period.status
            },
            status=status.HTTP_200_OK
        )
