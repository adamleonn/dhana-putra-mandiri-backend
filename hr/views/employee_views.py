from rest_framework import viewsets, permissions
from core.permissions import DEFAULT_PERMISSIONS, MANAGEMENT, DIREKTUR_ADMIN
from hr.models import Employee
from hr.serializers import EmployeeSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().select_related('user').prefetch_related(
        'mutations__approved_by', 'labor_records__recorded_by'
    )
    serializer_class = EmployeeSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': MANAGEMENT, 'write': DIREKTUR_ADMIN}
    filterset_fields = ['department', 'employment_status', 'is_active']
    search_fields = ['employee_id', 'full_name', 'phone', 'email']

