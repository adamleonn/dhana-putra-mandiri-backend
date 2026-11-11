from rest_framework import viewsets, permissions
from core.permissions import IsDirektur, IsAdminOps, IsStakeholderReadOnly
from hr.models import Employee
from hr.serializers import EmployeeSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().select_related('user').prefetch_related(
        'mutations__approved_by', 'labor_records__recorded_by'
    )
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['department', 'employment_status', 'is_active']
    search_fields = ['employee_id', 'full_name', 'phone', 'email']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsDirektur() | IsAdminOps())]
        return super().get_permissions()
