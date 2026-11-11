from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from core.permissions import IsDirektur, IsAccounting, IsStakeholderReadOnly
from hr.models import Employee, PayrollSlip
from hr.serializers import PayrollSlipSerializer
from hr.services.payroll_service import generate_employee_payroll, approve_payroll_slip


class PayrollSlipViewSet(viewsets.ModelViewSet):
    queryset = PayrollSlip.objects.all().select_related(
        'employee', 'accrual_journal_entry', 'payment', 'approved_by', 'paid_by'
    )
    serializer_class = PayrollSlipSerializer
    permission_classes = [permissions.IsAuthenticated, IsStakeholderReadOnly]
    filterset_fields = ['status', 'period_month', 'period_year', 'employee']
    search_fields = ['slip_number', 'employee__full_name', 'employee__employee_id']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), (IsAccounting() | IsDirektur())]
        return super().get_permissions()

    @action(detail=False, methods=['post'], url_path='generate_monthly')
    def generate_monthly(self, request):
        period_month = int(request.data.get('period_month', 0))
        period_year = int(request.data.get('period_year', 0))

        if not (1 <= period_month <= 12) or period_year <= 2000:
            return Response(
                {'error': "Parameter 'period_month' (1-12) dan 'period_year' yang valid wajib diisi."},
                status=status.HTTP_400_BAD_REQUEST
            )

        employees = Employee.objects.filter(is_active=True)
        created_slips = []
        for emp in employees:
            slip = generate_employee_payroll(
                employee=emp,
                period_month=period_month,
                period_year=period_year,
                actor=request.user
            )
            created_slips.append(slip)

        serializer = self.get_serializer(created_slips, many=True)
        return Response(
            {
                'message': f"Berhasil membuat {len(created_slips)} slip gaji untuk periode {period_month}/{period_year}.",
                'results': serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'])
    def generate(self, request):
        employee_id = request.data.get('employee')
        period_month = int(request.data.get('period_month', 0))
        period_year = int(request.data.get('period_year', 0))
        overtime = Decimal(str(request.data.get('overtime_allowance', '0.00')))
        bonus = Decimal(str(request.data.get('bonus_allowance', '0.00')))
        deductions = Decimal(str(request.data.get('deductions', '0.00')))
        notes = request.data.get('notes', '')

        if not employee_id or not (1 <= period_month <= 12) or period_year <= 2000:
            return Response(
                {'error': "Valid employee, period_month (1-12), and period_year are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            employee = Employee.objects.get(pk=employee_id)
            slip = generate_employee_payroll(
                employee=employee,
                period_month=period_month,
                period_year=period_year,
                overtime_allowance=overtime,
                bonus_allowance=bonus,
                deductions=deductions,
                notes=notes,
                actor=request.user
            )
            serializer = self.get_serializer(slip)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Employee.DoesNotExist:
            return Response({'error': "Karyawan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsDirektur])
    def approve(self, request, pk=None):
        slip = self.get_object()
        try:
            approved_slip = approve_payroll_slip(slip, request.user)
            serializer = self.get_serializer(approved_slip)
            return Response(
                {
                    'message': f"Slip gaji {slip.slip_number} berhasil di-approve oleh Direktur. Jurnal akrual terbit.",
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
