from rest_framework import serializers
from core.mixins import RoleFilteredSerializerMixin
from hr.models import Employee, PayrollSlip, EmployeeMutation, LaborRecord


class EmployeeMutationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = EmployeeMutation
        fields = [
            'id',
            'employee',
            'employee_name',
            'mutation_date',
            'effective_date',
            'mutation_type',
            'previous_department',
            'new_department',
            'previous_position',
            'new_position',
            'previous_salary',
            'new_salary',
            'reason',
            'approved_by',
            'approved_by_name',
            'is_applied',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['is_applied', 'approved_by', 'created_at', 'updated_at']


class LaborRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)

    class Meta:
        model = LaborRecord
        fields = [
            'id',
            'employee',
            'employee_name',
            'record_date',
            'record_type',
            'title',
            'description',
            'hours',
            'hourly_rate',
            'recorded_by',
            'recorded_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['recorded_by', 'created_at', 'updated_at']


class EmployeeSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    mutations = EmployeeMutationSerializer(many=True, read_only=True)
    labor_records = LaborRecordSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'employee_id',
            'user',
            'full_name',
            'email',
            'phone',
            'national_id',
            'tax_id',
            'department',
            'position',
            'employment_status',
            'joined_date',
            'termination_date',
            'base_salary',
            'standard_allowance',
            'bank_name',
            'bank_account_number',
            'bank_account_holder',
            'bpjs_tk_number',
            'bpjs_kes_number',
            'mutations',
            'labor_records',
            'is_active',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ret

        user = request.user
        is_direktur = user.is_superuser or user.groups.filter(name='Direktur').exists()
        if not is_direktur:
            # Mask sensitive HR and bank fields
            ret.pop('base_salary', None)
            ret.pop('standard_allowance', None)
            ret.pop('bank_account_number', None)
            ret.pop('national_id', None)

        return ret


class PayrollSlipSerializer(RoleFilteredSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_nik = serializers.CharField(source='employee.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.get_full_name', read_only=True)

    class Meta:
        model = PayrollSlip
        fields = [
            'id',
            'slip_number',
            'employee',
            'employee_nik',
            'employee_name',
            'period_month',
            'period_year',
            'base_salary',
            'allowances',
            'deductions',
            'net_salary',
            'payment_date',
            'status',
            'accrual_journal_entry',
            'payment',
            'approved_by',
            'approved_by_name',
            'approved_at',
            'paid_by',
            'paid_by_name',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'slip_number', 'status', 'accrual_journal_entry', 'payment',
            'approved_by', 'approved_at', 'paid_by', 'created_at', 'updated_at'
        ]
