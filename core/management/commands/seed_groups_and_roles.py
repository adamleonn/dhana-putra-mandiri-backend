from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Seed standard Enterprise Groups and Role Permissions for CV Dhana Putra Mandiri"

    def handle(self, *args, **options):
        self.stdout.write("Seeding enterprise role groups and permissions...")

        groups_config = {
            'Direktur': {
                'description': 'Super-Role: Full CRUD access + exclusive accounting period close/reopen privileges.',
                'all_perms': True,
            },
            'Admin': {
                'description': 'Operasional Admin: Draft invoices & deliveries, cash/bank mutations, receive customer payments.',
                'perms': [
                    'add_customer', 'change_customer', 'view_customer',
                    'add_supplier', 'change_supplier', 'view_supplier',
                    'add_salesinvoice', 'change_salesinvoice', 'view_salesinvoice',
                    'add_delivery', 'change_delivery', 'view_delivery',
                    'add_payment', 'change_payment', 'view_payment',
                    'view_product', 'view_goodsreceipt', 'add_goodsreceipt',
                ]
            },
            'Sales': {
                'description': 'Sales team: Draft invoices, deliveries, and discounts. Restricted from viewing HPP or General Ledger.',
                'perms': [
                    'view_customer', 'add_customer', 'change_customer',
                    'view_product',
                    'add_salesinvoice', 'change_salesinvoice', 'view_salesinvoice',
                    'add_delivery', 'change_delivery', 'view_delivery',
                ]
            },
            'Gudang': {
                'description': 'Warehouse team: Confirm GoodsReceipt and Delivery. Monetary values strictly stripped.',
                'perms': [
                    'view_product',
                    'view_goodsreceipt', 'change_goodsreceipt',
                    'view_delivery', 'change_delivery',
                    'add_laborrecord', 'view_laborrecord',
                    'view_stockmovement',
                ]
            },
            'Finance': {
                'description': 'Kasir / Keuangan: Cash and bank mutations, AR/AP payments. No access to alter physical stock.',
                'perms': [
                    'view_customer', 'view_supplier',
                    'view_salesinvoice', 'view_goodsreceipt',
                    'add_payment', 'change_payment', 'view_payment',
                    'view_chartofaccounts', 'view_payrollslip',
                ]
            },
            'Accounting': {
                'description': 'Accounting team: General Ledger audit, Debit Notes, revise invoices, submit period close.',
                'perms': [
                    'view_customer', 'view_supplier', 'view_product',
                    'view_goodsreceipt', 'view_delivery',
                    'view_salesinvoice', 'change_salesinvoice',
                    'add_debitnote', 'change_debitnote', 'view_debitnote',
                    'view_chartofaccounts', 'add_chartofaccounts', 'change_chartofaccounts',
                    'view_generalledger', 'add_generalledger',
                    'view_accountingperiod', 'change_accountingperiod',
                    'view_payrollslip', 'add_payrollslip', 'change_payrollslip',
                ]
            },
            'Stakeholder': {
                'description': 'Executive management: Read-only access to reports and financial dashboards.',
                'perms': [
                    'view_customer', 'view_supplier', 'view_product',
                    'view_goodsreceipt', 'view_delivery', 'view_stockmovement',
                    'view_salesinvoice', 'view_debitnote', 'view_payment',
                    'view_generalledger', 'view_chartofaccounts', 'view_accountingperiod',
                    'view_employee', 'view_payrollslip',
                ]
            }
        }

        all_permissions = {p.codename: p for p in Permission.objects.all()}

        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if config.get('all_perms'):
                group.permissions.set(Permission.objects.all())
                self.stdout.write(self.style.SUCCESS(f"  [+] Group '{group_name}' configured with ALL permissions."))
            else:
                assigned_perms = []
                for codename in config.get('perms', []):
                    if codename in all_permissions:
                        assigned_perms.append(all_permissions[codename])
                group.permissions.set(assigned_perms)
                self.stdout.write(self.style.SUCCESS(f"  [+] Group '{group_name}' configured with {len(assigned_perms)} permissions."))

        self.stdout.write(self.style.SUCCESS("All enterprise groups and roles seeded successfully!"))

