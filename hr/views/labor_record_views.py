from rest_framework import viewsets, permissions
from config.permissions import IsAccountingStaff, IsDirekturOrSuperuser
from hr.models import LaborRecord
from hr.serializers import LaborRecordSerializer


class LaborRecordViewSet(viewsets.ModelViewSet):
    """
    Catatan Tenaga Kerja (Log Harian, Lembur, SP, Insiden, Apresiasi).
    """
    queryset = LaborRecord.objects.all().select_related('employee', 'recorded_by')
    serializer_class = LaborRecordSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccountingStaff | IsDirekturOrSuperuser)]

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

