from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.management import call_command
from finance.models import ChartOfAccounts


class Command(BaseCommand):
    help = "Seed initial Chart of Accounts, standard RBAC Groups & Permissions for CV Dhana Putra Mandiri"

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding Chart of Accounts (COA) ---")
        coa_data = [
            # Aset Lancar
            ('1110', 'Kas Tunai Kantor', 'ASSET', 'CURRENT_ASSET', True, 'Kas operasional kasir tunai'),
            ('1120', 'Bank Central Asia (BCA)', 'ASSET', 'CURRENT_ASSET', True, 'Rekening giro/operasional utama BCA'),
            ('1121', 'Bank Mandiri', 'ASSET', 'CURRENT_ASSET', True, 'Rekening penampungan penerimaan penjualan'),
            ('1130', 'Piutang Usaha (AR)', 'ASSET', 'CURRENT_ASSET', False, 'Piutang dagang pelanggan/outlet'),
            ('1140', 'Persediaan Minyak Goreng (Inventory Asset)', 'ASSET', 'CURRENT_ASSET', False, 'Nilai persediaan barang dagang dinilai dengan Moving Average HPP'),

            # Kewajiban
            ('2110', 'Hutang Usaha (AP)', 'LIABILITY', 'CURRENT_LIABILITY', False, 'Hutang dagang kepada supplier pabrikan minyak'),
            ('2120', 'Hutang Gaji & Upah (Payroll Payable)', 'LIABILITY', 'CURRENT_LIABILITY', False, 'Akrual kewajiban gaji karyawan'),
            ('2130', 'Hutang Ongkos Bongkar Muat', 'LIABILITY', 'CURRENT_LIABILITY', False, 'Kewajiban ongkos kuli bongkar supplier'),

            # Ekuitas
            ('3100', 'Modal Disetor', 'EQUITY', 'EQUITY', False, 'Modal awal pemilik CV Dhana Putra Mandiri'),
            ('3200', 'Laba Ditahan', 'EQUITY', 'EQUITY', False, 'Akumulasi laba periode berjalan/sebelumnya'),

            # Pendapatan
            ('4100', 'Pendapatan Penjualan Minyak Goreng', 'REVENUE', 'SALES', False, 'Penjualan kotor ke toko/distributor/grosir'),
            ('4200', 'Diskon & Potongan Penjualan', 'REVENUE', 'SALES', False, 'Potongan penjualan promosi sales'),

            # Beban Pokok Penjualan (HPP / COGS)
            ('5100', 'Harga Pokok Penjualan (COGS / HPP)', 'EXPENSE', 'COGS', False, 'HPP minyak goreng termasuk alokasi biaya angkut supplier'),

            # Beban Operasional
            ('6100', 'Beban Operasional Umum & Kantor', 'EXPENSE', 'ADMIN_EXPENSE', False, 'Biaya administrasi dan utilitas kantor'),
            ('6110', 'Beban Gaji & Upah Karyawan', 'EXPENSE', 'LABOR_EXPENSE', False, 'Gaji pokok, lembur, dan tunjangan pegawai'),
            ('6120', 'Beban Bongkar Muat (Kuli Bongkar)', 'EXPENSE', 'LABOR_EXPENSE', False, 'Biaya bongkar barang masuk dari pabrik / supplier'),
            ('6130', 'Beban Transportasi & Bahan Bakar Armada', 'EXPENSE', 'TRANSPORT_EXPENSE', False, 'BBM dan tol armada pengiriman'),
        ]

        for code, name, acc_type, rep_group, is_cash, desc in coa_data:
            coa, created = ChartOfAccounts.objects.get_or_create(
                account_code=code,
                defaults={
                    'name': name,
                    'account_type': acc_type,
                    'report_group': rep_group,
                    'is_cash_bank': is_cash,
                    'is_postable': True,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  [+] Created COA: {code} - {name}"))
            else:
                self.stdout.write(f"  [*] COA exists: {code} - {name}")

        self.stdout.write("--- Seeding Groups & Roles ---")
        call_command('seed_groups_and_roles')
