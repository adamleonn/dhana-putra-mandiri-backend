from rest_framework import viewsets, permissions
from core.permissions import IsDirektur, IsAdminOps, IsStakeholderReadOnly
from hr.models import EmployeeMutation
from hr.serializers import EmployeeMutationSerializer
from hr.services.payroll_service import apply_employee_mutation


class EmployeeMutationViewSet(viewsets.ModelViewSet):
    queryset = EmployeeMutation.objects.all().select_related('employee', 'approved_by')
    serializer_class = EmployeeMutationSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['mutation_type', 'is_applied', 'employee']
    search_fields = ['employee__full_name', 'reason']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsDirektur() | IsAdminOps())]
        return super().get_permissions()

    def perform_create(self, serializer):
        mutation = serializer.save(approved_by=self.request.user)
        apply_employee_mutation(mutation, self.request.user)
