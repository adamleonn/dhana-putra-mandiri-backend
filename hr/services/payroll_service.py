from decimal import Decimal
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from hr.models import Employee, PayrollSlip, EmployeeMutation
from finance.services.journal_service import create_journal_entry, get_open_period
from core.services.sequence import next_number
from core.services.audit import log_audit


@transaction.atomic
def generate_employee_payroll(
    employee: Employee,
    period_month: int,
    period_year: int,
    overtime_allowance: Decimal = Decimal('0.00'),
    bonus_allowance: Decimal = Decimal('0.00'),
    deductions: Decimal = Decimal('0.00'),
    notes: str = "",
    actor=None
) -> PayrollSlip:
    """
    Generate draf slip gaji bulanan karyawan.
    """
    if not employee.is_active:
        raise ValidationError(f"Tidak dapat membuat slip gaji untuk karyawan non-aktif '{employee.full_name}'.")

    total_allowances = employee.standard_allowance + overtime_allowance + bonus_allowance
    net_salary = employee.base_salary + total_allowances - deductions

    if net_salary < Decimal('0.00'):
        raise ValidationError("Gaji bersih (net salary) tidak boleh negatif.")

    existing_slip = PayrollSlip.objects.filter(
        employee=employee,
        period_month=period_month,
        period_year=period_year
    ).first()

    if existing_slip:
        if existing_slip.status in ['approved', 'paid']:
            return existing_slip
        existing_slip.base_salary = employee.base_salary
        existing_slip.allowances = total_allowances
        existing_slip.deductions = deductions
        existing_slip.net_salary = net_salary
        existing_slip.notes = notes
        existing_slip.save(update_fields=['base_salary', 'allowances', 'deductions', 'net_salary', 'notes', 'updated_at'])
        return existing_slip

    slip_date = date(period_year, period_month, 1)
    slip_number = next_number('SLIP', slip_date)

    slip = PayrollSlip.objects.create(
        slip_number=slip_number,
        employee=employee,
        period_month=period_month,
        period_year=period_year,
        base_salary=employee.base_salary,
        allowances=total_allowances,
        deductions=deductions,
        net_salary=net_salary,
        status='draft',
        notes=notes,
        created_by=actor
    )

    log_audit(
        actor=actor,
        action='CREATE',
        instance=slip,
        changes={
            'slip_number': slip_number,
            'net_salary': str(net_salary),
            'employee': employee.full_name
        }
    )

    return slip


@transaction.atomic
def approve_payroll_slip(slip: PayrollSlip, approver) -> PayrollSlip:
    """
    Persetujuan (Approval) Slip Gaji oleh Direktur:
    Membukukan Jurnal Akrual:
    Dr Beban Gaji Karyawan (6110)
    Cr Hutang Gaji Karyawan (2120)
    """
    if slip.status != 'draft':
        raise ValidationError(f"Slip gaji '{slip.slip_number}' berstatus '{slip.status}'. Hanya status draf yang dapat di-approve.")

    today = timezone.now().date()
    get_open_period(today)

    journal = create_journal_entry(
        transaction_date=today,
        reference_type='PAYROLL_ACCRUAL',
        reference_id=slip.slip_number,
        description=f"Akrual Beban Gaji {slip.employee.full_name} ({slip.period_month}/{slip.period_year})",
        lines=[
            {
                'account_code': '6110',
                'debit': slip.net_salary,
                'credit': Decimal('0.00'),
                'memo': f"Beban Gaji Karyawan {slip.employee.full_name}"
            },
            {
                'account_code': '2120',
                'debit': Decimal('0.00'),
                'credit': slip.net_salary,
                'memo': f"Pengakuan Hutang Gaji Slip #{slip.slip_number}"
            }
        ],
        posted_by=approver
    )

    slip.status = 'approved'
    slip.approved_by = approver
    slip.approved_at = timezone.now()
    slip.accrual_journal_entry = journal
    slip.save(update_fields=['status', 'approved_by', 'approved_at', 'accrual_journal_entry', 'updated_at'])

    log_audit(
        actor=approver,
        action='APPROVE',
        instance=slip,
        changes={
            'status': 'approved',
            'accrual_journal': journal.transaction_number
        }
    )

    return slip


@transaction.atomic
def apply_employee_mutation(mutation: EmployeeMutation, approver) -> EmployeeMutation:
    """
    Menerapkan mutasi jabatan / divisi / gaji karyawan secara atomik.
    """
    if mutation.is_applied:
        raise ValidationError("Mutasi ini sudah pernah diterapkan sebelumnya.")

    employee = mutation.employee
    mutation.previous_department = employee.department
    mutation.previous_position = employee.position
    mutation.previous_salary = employee.base_salary

    employee.department = mutation.new_department
    employee.position = mutation.new_position
    employee.base_salary = mutation.new_salary
    employee.save(update_fields=['department', 'position', 'base_salary', 'updated_at'])

    mutation.is_applied = True
    mutation.approved_by = approver
    mutation.save(update_fields=['previous_department', 'previous_position', 'previous_salary', 'is_applied', 'approved_by', 'updated_at'])

    log_audit(
        actor=approver,
        action='APPROVE',
        instance=mutation,
        changes={
            'employee': employee.full_name,
            'new_department': mutation.new_department,
            'new_position': mutation.new_position,
            'new_salary': str(mutation.new_salary)
        }
    )

    return mutation
