from rest_framework import serializers
from .models import Employee, PayrollSlip, EmployeeMutation, LaborRecord


class EmployeeMutationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    mutation_type_display = serializers.CharField(source='get_mutation_type_display', read_only=True)

    class Meta:
        model = EmployeeMutation
        fields = [
            'id',
            'employee',
            'employee_name',
            'mutation_date',
            'mutation_type',
            'mutation_type_display',
            'previous_department',
            'new_department',
            'previous_position',
            'new_position',
            'previous_salary',
            'new_salary',
            'reason',
            'approved_by',
            'approved_by_name',
            'created_at',
            'updated_at',
        ]


class LaborRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)

    class Meta:
        model = LaborRecord
        fields = [
            'id',
            'employee',
            'employee_name',
            'record_date',
            'record_type',
            'record_type_display',
            'title',
            'description',
            'hours',
            'recorded_by',
            'recorded_by_name',
            'created_at',
            'updated_at',
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(source='get_department_display', read_only=True)
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
            'department',
            'department_display',
            'position',
            'base_salary',
            'standard_allowance',
            'bank_name',
            'bank_account_number',
            'bank_account_holder',
            'is_active',
            'joined_date',
            'mutations',
            'labor_records',
            'created_at',
            'updated_at',
        ]


class PayrollSlipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_id', read_only=True)
    department = serializers.CharField(source='employee.get_department_display', read_only=True)
    journal_entry_number = serializers.CharField(source='journal_entry.entry_number', read_only=True)

    class Meta:
        model = PayrollSlip
        fields = [
            'id',
            'slip_number',
            'employee',
            'employee_code',
            'employee_name',
            'department',
            'period_month',
            'period_year',
            'base_salary',
            'allowances',
            'deductions',
            'net_salary',
            'payment_date',
            'status',
            'journal_entry',
            'journal_entry_number',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['slip_number', 'journal_entry', 'created_at', 'updated_at']
