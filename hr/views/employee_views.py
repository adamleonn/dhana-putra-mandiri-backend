from rest_framework import viewsets, permissions
from config.permissions import IsAccountingStaff, IsDirekturOrSuperuser
from hr.models import Employee
from hr.serializers import EmployeeSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().select_related('user').prefetch_related('mutations__approved_by', 'labor_records__recorded_by')
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccountingStaff | IsDirekturOrSuperuser)]
