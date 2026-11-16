from rest_framework import viewsets, permissions
from core.permissions import DEFAULT_PERMISSIONS, MANAGEMENT, DIREKTUR_ADMIN
from hr.models import EmployeeMutation
from hr.serializers import EmployeeMutationSerializer
from hr.services.payroll_service import apply_employee_mutation


class EmployeeMutationViewSet(viewsets.ModelViewSet):
    queryset = EmployeeMutation.objects.all().select_related('employee', 'approved_by')
    serializer_class = EmployeeMutationSerializer
    permission_classes = DEFAULT_PERMISSIONS
    role_access = {'read': MANAGEMENT, 'write': DIREKTUR_ADMIN}
    filterset_fields = ['mutation_type', 'is_applied', 'employee']
    search_fields = ['employee__full_name', 'reason']


    def perform_create(self, serializer):
        mutation = serializer.save(approved_by=self.request.user)
        apply_employee_mutation(mutation, self.request.user)
