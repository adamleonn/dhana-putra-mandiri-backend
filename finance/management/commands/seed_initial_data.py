from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from finance.models import ChartOfAccounts, AccountingPeriod
from inventory.models import Product, GoodsReceipt, Delivery
from hr.models import Employee, PayrollSlip, EmployeeMutation, LaborRecord


class Command(BaseCommand):
    help = "Seed initial Chart of Accounts, standard RBAC Groups & Permissions for CV Dhana Putra Mandiri"

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding Chart of Accounts (COA) ---")
        coa_data = [
            # Aset Lancar
            ('1110', 'Kas Tunai Kantor', 'ASSET', 'Kas operasional kasir tunai'),
            ('1120', 'Bank Central Asia (BCA)', 'ASSET', 'Rekening giro/operasional utama BCA'),
            ('1121', 'Bank Mandiri', 'ASSET', 'Rekening penampungan penerimaan penjualan'),
            ('1130', 'Piutang Usaha (AR)', 'ASSET', 'Piutang dagang pelanggan/outlet'),
            ('1140', 'Persediaan Minyak Goreng (Inventory Asset)', 'ASSET', 'Nilai persediaan barang dagang dinilai dengan Moving Average HPP'),
            # Kewajiban
            ('2110', 'Hutang Usaha (AP)', 'LIABILITY', 'Hutang dagang kepada supplier pabrikan minyak'),
            ('2120', 'Hutang Gaji & Upah (Payroll Payable)', 'LIABILITY', 'Akrual kewajiban gaji karyawan'),
            ('2130', 'Hutang Ongkos Bongkar Muat', 'LIABILITY', 'Kewajiban ongkos kuli bongkar supplier'),
            # Ekuitas
            ('3100', 'Modal Disetor', 'EQUITY', 'Modal awal pemilik CV Dhana Putra Mandiri'),
            ('3200', 'Laba Ditahan', 'EQUITY', 'Akumulasi laba periode berjalan/sebelumnya'),
            # Pendapatan
            ('4100', 'Pendapatan Penjualan Minyak Goreng', 'REVENUE', 'Penjualan kotor ke toko/distributor/grosir'),
            ('4200', 'Diskon & Potongan Penjualan', 'REVENUE', 'Potongan penjualan promosi sales'),
            # Beban Pokok Penjualan (HPP / COGS)
            ('5100', 'Harga Pokok Penjualan (COGS / HPP)', 'COGS', 'HPP minyak goreng termasuk alokasi biaya angkut supplier'),
            # Beban Operasional
            ('6100', 'Beban Bongkar Muat (Kuli Bongkar)', 'EXPENSE', 'Biaya bongkar barang masuk dari pabrik / supplier'),
            ('6200', 'Beban Gaji & Upah Karyawan', 'EXPENSE', 'Gaji pokok, lembur, dan tunjangan pegawai'),
            ('6300', 'Beban Transportasi & Bahan Bakar Armada', 'EXPENSE', 'BBM dan tol armada pengiriman'),
            ('6400', 'Beban Operasional Kantor & Umum', 'EXPENSE', 'Biaya administrasi dan utilitas kantor'),
        ]

        for code, name, acc_type, desc in coa_data:
            coa, created = ChartOfAccounts.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'account_type': acc_type,
                    'description': desc,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created COA: {code} - {name}"))
            else:
                self.stdout.write(f"COA exists: {code} - {name}")

        self.stdout.write("--- Seeding RBAC Groups and Core Permissions ---")
        # 1. Direktur (SuperAdmin)
        direktur_group, _ = Group.objects.get_or_create(name='Direktur')
        all_app_perms = Permission.objects.filter(
            content_type__app_label__in=['inventory', 'finance', 'hr', 'auth']
        )
        direktur_group.permissions.set(all_app_perms)
        self.stdout.write(self.style.SUCCESS(f"Configured group 'Direktur' with FULL CRUD ({all_app_perms.count()} permissions)."))

        # 2. Stakeholder (Read-Only across all modules)
        stakeholder_group, _ = Group.objects.get_or_create(name='Stakeholder')
        read_only_perms = Permission.objects.filter(
            codename__startswith='view_'
        )
        stakeholder_group.permissions.set(read_only_perms)
        self.stdout.write(self.style.SUCCESS(f"Configured group 'Stakeholder' with Read-Only ({read_only_perms.count()} permissions)."))

        # 3. Admin (Gabungan Penjualan & Keuangan)
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        admin_perms = Permission.objects.filter(
            codename__in=[
                'view_product',
                'add_salesinvoice', 'change_salesinvoice', 'view_salesinvoice',
                'add_salesinvoiceitem', 'change_salesinvoiceitem', 'delete_salesinvoiceitem', 'view_salesinvoiceitem',
                'view_goodsreceipt', 'view_debitnote',
                'add_payment', 'change_payment', 'view_payment',
                'view_chartofaccounts', 'view_payrollslip'
            ]
        )
        admin_group.permissions.set(admin_perms)
        self.stdout.write(self.style.SUCCESS(f"Configured group 'Admin' (Sales + Finance) with {admin_perms.count()} permissions."))

        groups_config = {
            'Sales': {
                'permissions': [
                    'view_product',
                    'add_salesinvoice',
                    'change_salesinvoice',
                    'view_salesinvoice',
                    'add_salesinvoiceitem',
                    'change_salesinvoiceitem',
                    'delete_salesinvoiceitem',
                    'view_salesinvoiceitem',
                ]
            },
            'Gudang': {
                'permissions': [
                    'view_product',
                    'add_goodsreceipt',
                    'change_goodsreceipt',
                    'view_goodsreceipt',
                    'add_goodsreceiptitem',
                    'change_goodsreceiptitem',
                    'view_goodsreceiptitem',
                    'add_delivery',
                    'change_delivery',
                    'view_delivery',
                    'add_deliveryitem',
                    'change_deliveryitem',
                    'view_deliveryitem',
                ]
            },
            'Finance': {
                'permissions': [
                    'view_salesinvoice',
                    'view_goodsreceipt',
                    'view_debitnote',
                    'add_payment',
                    'change_payment',
                    'view_payment',
                    'view_chartofaccounts',
                    'view_payrollslip',
                ]
            },
            'Accounting': {
                'permissions': [
                    'view_product',
                    'view_goodsreceipt',
                    'view_delivery',
                    'view_salesinvoice',
                    'change_salesinvoice',
                    'add_debitnote',
                    'change_debitnote',
                    'view_debitnote',
                    'add_generalledger',
                    'change_generalledger',
                    'view_generalledger',
                    'add_generalledgerline',
                    'change_generalledgerline',
                    'view_generalledgerline',
                    'view_chartofaccounts',
                    'add_chartofaccounts',
                    'change_chartofaccounts',
                    'view_payment',
                    'add_payrollslip',
                    'change_payrollslip',
                    'view_payrollslip',
                    'view_employee',
                    'add_employeemutation',
                    'change_employeemutation',
                    'view_employeemutation',
                    'add_laborrecord',
                    'change_laborrecord',
                    'view_laborrecord',
                ]
            },
        }

        for group_name, cfg in groups_config.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            perm_codenames = cfg['permissions']
            perms = Permission.objects.filter(codename__in=perm_codenames)
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"Configured group '{group_name}' with {perms.count()} permissions."))

        self.stdout.write(self.style.SUCCESS("Initial data seeding completed successfully!"))
