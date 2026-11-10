from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from config.permissions import IsAccountingStaff, IsFinanceKasir, IsDirekturOrSuperuser
from hr.models import Employee, PayrollSlip
from hr.serializers import PayrollSlipSerializer
from hr.services import generate_employee_payroll, approve_and_disburse_payroll


class PayrollSlipViewSet(viewsets.ModelViewSet):
    queryset = PayrollSlip.objects.all().select_related('employee', 'journal_entry')
    serializer_class = PayrollSlipSerializer
    permission_classes = [permissions.IsAuthenticated, (IsAccountingStaff | IsFinanceKasir | IsDirekturOrSuperuser)]

    @action(detail=False, methods=['post'], permission_classes=[IsAccountingStaff | IsDirekturOrSuperuser])
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
                {'error': 'Valid employee, period_month (1-12), and period_year are required.'},
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
                notes=notes
            )
            serializer = self.get_serializer(slip)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsFinanceKasir | IsDirekturOrSuperuser])
    def disburse(self, request, pk=None):
        slip = self.get_object()
        account_code = request.data.get('disbursement_account_code', '1120')
        try:
            paid_slip = approve_and_disburse_payroll(
                slip=slip,
                disbursed_by=request.user,
                disbursement_account_code=account_code
            )
            serializer = self.get_serializer(paid_slip)
            return Response(
                {
                    'message': 'Payroll disbursed successfully. Expense journal posted to General Ledger.',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValidationError as ve:
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
