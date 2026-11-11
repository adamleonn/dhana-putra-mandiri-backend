from rest_framework import viewsets, permissions
from core.permissions import IsGudang, IsAdminOps, IsDirektur, IsStakeholderReadOnly
from hr.models import LaborRecord
from hr.serializers import LaborRecordSerializer


class LaborRecordViewSet(viewsets.ModelViewSet):
    queryset = LaborRecord.objects.all().select_related('employee', 'recorded_by')
    serializer_class = LaborRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['record_type', 'employee', 'record_date']
    search_fields = ['employee__full_name', 'title', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsGudang() | IsAdminOps() | IsDirektur())]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
