from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from hr.models import Employee, PayrollSlip
from finance.services import create_journal_entry


@transaction.atomic
def generate_employee_payroll(
    employee: Employee,
    period_month: int,
    period_year: int,
    overtime_allowance: Decimal = Decimal('0.00'),
    bonus_allowance: Decimal = Decimal('0.00'),
    deductions: Decimal = Decimal('0.00'),
    notes: str = ""
) -> PayrollSlip:
    if not employee.is_active:
        raise ValidationError(f"Cannot generate payroll for inactive employee '{employee.full_name}'.")

    total_allowances = employee.standard_allowance + overtime_allowance + bonus_allowance
    net_salary = employee.base_salary + total_allowances - deductions

    if net_salary < Decimal('0.00'):
        raise ValidationError("Net salary cannot be negative.")

    from config.sequence_generator import generate_document_number
    existing_slip = PayrollSlip.objects.filter(
        employee=employee,
        period_month=period_month,
        period_year=period_year
    ).first()

    if existing_slip:
        if existing_slip.status == 'paid':
            return existing_slip
        existing_slip.base_salary = employee.base_salary
        existing_slip.allowances = total_allowances
        existing_slip.deductions = deductions
        existing_slip.net_salary = net_salary
        existing_slip.notes = notes
        existing_slip.save()
        return existing_slip

    slip_number = generate_document_number('SLIP')
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
        notes=notes
    )
    return slip


@transaction.atomic
def approve_and_disburse_payroll(
    slip: PayrollSlip,
    disbursed_by,
    disbursement_account_code: str = '1120'
) -> PayrollSlip:
    if slip.status == 'paid':
        return slip

    today = timezone.now().date()
    journal_lines = [
        {
            'account_code': '6200',
            'debit': slip.net_salary,
            'credit': Decimal('0.00'),
            'memo': f"Beban Gaji {slip.employee.full_name} ({slip.period_month}/{slip.period_year})"
        },
        {
            'account_code': disbursement_account_code,
            'debit': Decimal('0.00'),
            'credit': slip.net_salary,
            'memo': f"Pembayaran Gaji Slip {slip.slip_number}"
        }
    ]

    from config.sequence_generator import generate_document_number
    jv_number = generate_document_number('JV', today)

    journal = create_journal_entry(
        entry_number=jv_number,
        transaction_date=today,
        reference_type='PAYROLL',
        reference_id=slip.slip_number,
        description=f"Payroll Disbursement for {slip.employee.full_name} [{slip.period_month}/{slip.period_year}]",
        lines=journal_lines,
        posted_by=disbursed_by
    )

    slip.status = 'paid'
    slip.payment_date = today
    slip.journal_entry = journal
    slip.save(update_fields=['status', 'payment_date', 'journal_entry'])

    return slip
