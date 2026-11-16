from rest_framework import viewsets, permissions
from core.permissions import DEFAULT_PERMISSIONS, READ_ALL, DIREKTUR, ADMIN, GUDANG
from hr.models import LaborRecord
from hr.serializers import LaborRecordSerializer


class LaborRecordViewSet(viewsets.ModelViewSet):
    queryset = LaborRecord.objects.all().select_related('employee', 'recorded_by')
    serializer_class = LaborRecordSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': READ_ALL, 'write': {DIREKTUR, ADMIN, GUDANG}}
    filterset_fields = ['record_type', 'employee', 'record_date']
    search_fields = ['employee__full_name', 'title', 'description']


    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
