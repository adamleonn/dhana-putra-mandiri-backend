from decimal import Decimal
from rest_framework import viewsets, permissions
from config.permissions import IsAccountingStaff, IsDirekturOrSuperuser
from hr.models import EmployeeMutation
from hr.serializers import EmployeeMutationSerializer


class EmployeeMutationViewSet(viewsets.ModelViewSet):
    """
    Riwayat mutasi, promosi, dan penyesuaian gaji karyawan.
    """
    queryset = EmployeeMutation.objects.all().select_related('employee', 'approved_by')
    serializer_class = EmployeeMutationSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccountingStaff | IsDirekturOrSuperuser)]

    def perform_create(self, serializer):
        mutation = serializer.save(approved_by=self.request.user)
        emp = mutation.employee
        if mutation.new_department:
            emp.department = mutation.new_department
        if mutation.new_position:
            emp.position = mutation.new_position
        if mutation.new_salary and mutation.new_salary > Decimal('0.00'):
            emp.base_salary = mutation.new_salary
        emp.save()

