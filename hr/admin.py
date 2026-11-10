from django.contrib import admin
from .models import Employee, PayrollSlip, EmployeeMutation, LaborRecord


class EmployeeMutationInline(admin.TabularInline):
    model = EmployeeMutation
    extra = 0
    fields = ('mutation_date', 'mutation_type', 'previous_department', 'new_department', 'previous_position', 'new_position', 'new_salary', 'approved_by')


class LaborRecordInline(admin.TabularInline):
    model = LaborRecord
    extra = 0
    fields = ('record_date', 'record_type', 'title', 'hours', 'recorded_by')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'full_name', 'department', 'position', 'base_salary', 'standard_allowance', 'is_active', 'joined_date')
    list_filter = ('department', 'is_active')
    search_fields = ('employee_id', 'full_name', 'email', 'phone')
    inlines = [EmployeeMutationInline, LaborRecordInline]


@admin.register(PayrollSlip)
class PayrollSlipAdmin(admin.ModelAdmin):
    list_display = ('slip_number', 'employee', 'period_month', 'period_year', 'net_salary', 'status', 'payment_date')
    list_filter = ('period_year', 'period_month', 'status')
    search_fields = ('slip_number', 'employee__full_name', 'employee__employee_id')


@admin.register(EmployeeMutation)
class EmployeeMutationAdmin(admin.ModelAdmin):
    list_display = ('employee', 'mutation_date', 'mutation_type', 'previous_position', 'new_position', 'new_salary', 'approved_by')
    list_filter = ('mutation_type', 'mutation_date')
    search_fields = ('employee__full_name', 'reason')


@admin.register(LaborRecord)
class LaborRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'record_date', 'record_type', 'title', 'hours', 'recorded_by')
    list_filter = ('record_type', 'record_date')
    search_fields = ('employee__full_name', 'title', 'description')
