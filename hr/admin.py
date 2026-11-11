from django.contrib import admin
from hr.models import Employee, PayrollSlip, EmployeeMutation, LaborRecord


class EmployeeMutationInline(admin.TabularInline):
    model = EmployeeMutation
    extra = 0
    readonly_fields = ['is_applied', 'approved_by']


class LaborRecordInline(admin.TabularInline):
    model = LaborRecord
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'department', 'position', 'employment_status', 'joined_date', 'is_active']
    search_fields = ['employee_id', 'full_name', 'phone', 'email']
    list_filter = ['department', 'employment_status', 'is_active']
    inlines = [EmployeeMutationInline, LaborRecordInline]


@admin.register(PayrollSlip)
class PayrollSlipAdmin(admin.ModelAdmin):
    list_display = ['slip_number', 'employee', 'period_month', 'period_year', 'net_salary', 'status', 'approved_by']
    search_fields = ['slip_number', 'employee__full_name']
    list_filter = ['status', 'period_year', 'period_month']


@admin.register(EmployeeMutation)
class EmployeeMutationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'mutation_date', 'effective_date', 'mutation_type', 'new_department', 'new_position', 'is_applied']
    search_fields = ['employee__full_name', 'reason']
    list_filter = ['mutation_type', 'is_applied']


@admin.register(LaborRecord)
class LaborRecordAdmin(admin.ModelAdmin):
    list_display = ['employee', 'record_date', 'record_type', 'title', 'hours', 'recorded_by']
    search_fields = ['employee__full_name', 'title']
    list_filter = ['record_type', 'record_date']
