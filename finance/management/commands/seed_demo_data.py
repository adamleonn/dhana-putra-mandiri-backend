from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from core.models import Customer, Supplier
from finance.models import ChartOfAccounts, AccountingPeriod
from inventory.models import Product, GoodsReceipt, GoodsReceiptItem, Delivery, DeliveryItem
from hr.models import Employee, PayrollSlip, EmployeeMutation, LaborRecord
from inventory.services import confirm_goods_receipt, confirm_delivery_atomic, calculate_abc_classification
from hr.services import generate_employee_payroll, approve_and_disburse_payroll

User = get_user_model()


class Command(BaseCommand):
    help = "Seed realistic demo dataset for CV Dhana Putra Mandiri"

    def handle(self, *args, **options):
        self.stdout.write("--- Seeding Demo Users & Groups ---")
        users_info = [
            ('direktur', 'Direktur123!', 'Direktur', 'Hendra', 'Wijaya', 'hendra@dhanaputra.co.id', 'direksi', 'Direktur Utama', Decimal('15000000.00'), Decimal('3000000.00')),
            ('admin', 'Admin123!', 'Admin', 'Dewi', 'Lestari', 'dewi.admin@dhanaputra.co.id', 'sales', 'Admin Operasional', Decimal('5500000.00'), Decimal('1200000.00')),
            ('sales', 'Sales123!', 'Sales', 'Siti', 'Nurhaliza', 'siti.sales@dhanaputra.co.id', 'sales', 'Sales Executive', Decimal('4500000.00'), Decimal('1500000.00')),
            ('gudang', 'Gudang123!', 'Gudang', 'Budi', 'Santoso', 'budi.gudang@dhanaputra.co.id', 'gudang', 'Kepala Gudang', Decimal('5000000.00'), Decimal('1000000.00')),
            ('kasir', 'Kasir123!', 'Finance', 'Rita', 'Kurnia', 'rita.kasir@dhanaputra.co.id', 'finance', 'Staf Kasir & Keuangan', Decimal('4800000.00'), Decimal('800000.00')),
            ('accounting', 'Accounting123!', 'Accounting', 'Arif', 'Wicaksono', 'arif.accounting@dhanaputra.co.id', 'accounting', 'Accounting Staff', Decimal('7500000.00'), Decimal('1500000.00')),
            ('stakeholder', 'Stakeholder123!', 'Stakeholder', 'Bambang', 'Soepomo', 'bambang.investor@dhanaputra.co.id', 'direksi', 'Komisaris', Decimal('0.00'), Decimal('0.00')),
        ]

        created_users = {}
        for username, pwd, group_name, first, last, email, dept, pos, salary, allowance in users_info:
            group, _ = Group.objects.get_or_create(name=group_name)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'email': email,
                    'is_staff': True,
                    'is_superuser': (username == 'direktur')
                }
            )
            user.set_password(pwd)
            user.save()
            user.groups.add(group)
            created_users[username] = user

            emp_id = f"EMP-{username.upper()}"
            Employee.objects.update_or_create(
                employee_id=emp_id,
                defaults={
                    'user': user,
                    'full_name': f"{first} {last}",
                    'email': email,
                    'phone': '0812-3456-7890',
                    'department': dept,
                    'position': pos,
                    'base_salary': salary,
                    'standard_allowance': allowance,
                    'bank_name': 'Bank Central Asia (BCA)',
                    'bank_account_number': '8830123456',
                    'bank_account_holder': f"{first} {last}",
                    'is_active': True,
                    'joined_date': timezone.now().date().replace(year=2023, month=1, day=1)
                }
            )

        self.stdout.write("--- Seeding Master Customers & Suppliers ---")
        customer, _ = Customer.objects.get_or_create(
            code='CUST-001',
            defaults={
                'name': 'Toko Berkah Minyak Sejahtera',
                'contact_person': 'H. Sulaiman',
                'phone': '0813-8899-7711',
                'email': 'toko.berkah@gmail.com',
                'address': 'Pasar Induk Kramat Jati Blok C No. 12',
                'credit_limit': Decimal('50000000.00')
            }
        )

        supplier, _ = Supplier.objects.get_or_create(
            code='SUPP-001',
            defaults={
                'name': 'PT Salim Ivomas Pratama Tbk',
                'contact_person': 'Bambang Irawan',
                'phone': '021-57958822',
                'email': 'sales@simp.co.id',
                'address': 'Sudirman Plaza, Indofood Tower Lt. 11, Jakarta Selatan'
            }
        )

        self.stdout.write("--- Seeding Accounting Period ---")
        today = timezone.now().date()
        current_period, _ = AccountingPeriod.objects.get_or_create(
            period_name=f"Periode {today.strftime('%B %Y')}",
            defaults={
                'start_date': today.replace(day=1),
                'end_date': today.replace(day=28),
                'status': 'OPEN'
            }
        )

        self.stdout.write("--- Seeding Cooking Oil Products ---")
        products_data = [
            ('BIM-SP-2L', 'Bimoli Spesial 2L (Dus 6 Pouch)', 'Bimoli', '2L', 'Karton', Decimal('12.00'), Decimal('215000.00'), Decimal('245000.00'), Decimal('25.00'), Decimal('350.00')),
            ('FLM-2L', 'Filma Minyak Goreng 2L (Dus 6 Pouch)', 'Filma', '2L', 'Karton', Decimal('12.00'), Decimal('210000.00'), Decimal('240000.00'), Decimal('20.00'), Decimal('280.00')),
            ('SNA-2L', 'Sania Royale 2L (Dus 6 Pouch)', 'Sania', '2L', 'Karton', Decimal('12.00'), Decimal('205000.00'), Decimal('232000.00'), Decimal('15.00'), Decimal('150.00')),
            ('SNC-2L', 'SunCo Minyak Goreng 2L (Dus 6 Pouch)', 'SunCo', '2L', 'Karton', Decimal('12.00'), Decimal('212000.00'), Decimal('242000.00'), Decimal('12.00'), Decimal('120.00')),
            ('MKT-1L', 'Minyakita 1L Bantal (Dus 12 Pouch)', 'Minyakita', '1L', 'Karton', Decimal('12.00'), Decimal('155000.00'), Decimal('172000.00'), Decimal('35.00'), Decimal('450.00')),
            ('CUR-18L', 'Minyak Curah CP10 Jerigen 18 Liter', 'Curah CP10', '18L', 'Jerigen', Decimal('18.00'), Decimal('265000.00'), Decimal('295000.00'), Decimal('10.00'), Decimal('80.00')),
        ]

        seeded_products = {}
        for sku, name, brand, size, uom, conv, hpp, price, daily_rate, initial_stock in products_data:
            p, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'brand': brand,
                    'package_size': size,
                    'uom': uom,
                    'conversion_factor': conv,
                    'moving_average_hpp': hpp,
                    'selling_price': price,
                    'daily_consumption_rate': daily_rate,
                    'current_stock': initial_stock,
                    'min_stock_level': daily_rate * Decimal('10.00'),
                    'is_active': True
                }
            )
            seeded_products[sku] = p

        calculate_abc_classification()

        self.stdout.write("--- Seeding Inbound Goods Receipt ---")
        receipt_num = f"GR/{today.strftime('%Y%m')}/0001"
        if not GoodsReceipt.objects.filter(receipt_number=receipt_num).exists():
            gr = GoodsReceipt.objects.create(
                receipt_number=receipt_num,
                supplier=supplier,
                supplier_name=supplier.name,
                po_reference='PO-202611-0089',
                receipt_date=today,
                transport_cost=Decimal('1500000.00'),
                unloading_cost=Decimal('250000.00'),
                created_by=created_users['admin'],
                notes='Penerimaan rutin pabrik'
            )
            GoodsReceiptItem.objects.create(
                goods_receipt=gr,
                product=seeded_products['BIM-SP-2L'],
                qty_ordered=Decimal('100.00'),
                qty_actual=Decimal('100.00'),
                purchase_price=Decimal('212000.00')
            )
            GoodsReceiptItem.objects.create(
                goods_receipt=gr,
                product=seeded_products['FLM-2L'],
                qty_ordered=Decimal('80.00'),
                qty_actual=Decimal('80.00'),
                purchase_price=Decimal('208000.00')
            )
            confirm_goods_receipt(gr, created_users['gudang'])

        self.stdout.write("--- Seeding Outbound Delivery ---")
        do_num = f"SJ/{today.strftime('%Y%m')}/0001"
        if not Delivery.objects.filter(delivery_number=do_num).exists():
            delivery = Delivery.objects.create(
                delivery_number=do_num,
                customer=customer,
                customer_name=customer.name,
                delivery_date=today,
                driver_name='Joko Susanto',
                vehicle_number='B 9234 KDA',
                sales_order_ref='SO-202611-0042',
                created_by=created_users['sales'],
                notes='Pengiriman toko grosir pasar induk'
            )
            DeliveryItem.objects.create(
                delivery=delivery,
                product=seeded_products['BIM-SP-2L'],
                qty=Decimal('30.00'),
                qty_delivered=Decimal('30.00')
            )
            DeliveryItem.objects.create(
                delivery=delivery,
                product=seeded_products['MKT-1L'],
                qty=Decimal('50.00'),
                qty_delivered=Decimal('48.00')
            )
            confirm_delivery_atomic(delivery, created_users['gudang'])

        self.stdout.write("--- Seeding Payroll Slip ---")
        emp_gudang = Employee.objects.get(employee_id='EMP-GUDANG')
        slip = generate_employee_payroll(
            employee=emp_gudang,
            period_month=today.month,
            period_year=today.year,
            overtime_allowance=Decimal('450000.00'),
            bonus_allowance=Decimal('200000.00'),
            deductions=Decimal('150000.00'),
            notes='Payroll bulan berjalan'
        )
        approve_and_disburse_payroll(slip, created_users['direktur'])

        emp_sales = Employee.objects.get(employee_id='EMP-SALES')
        EmployeeMutation.objects.get_or_create(
            employee=emp_sales,
            mutation_date=today.replace(day=1),
            defaults={
                'mutation_type': 'PROMOTION',
                'previous_department': 'sales',
                'new_department': 'sales',
                'previous_position': 'Junior Sales Representative',
                'new_position': 'Senior Sales Executive',
                'previous_salary': Decimal('3800000.00'),
                'new_salary': Decimal('4500000.00'),
                'reason': 'Pencapaian target penjualan minyak goreng kuartal 3 melampaui 120%',
                'approved_by': created_users['direktur']
            }
        )

        LaborRecord.objects.get_or_create(
            employee=emp_gudang,
            record_date=today,
            defaults={
                'record_type': 'OVERTIME_LOG',
                'title': 'Lembur Bongkar Muat Fuso Minyak Curah',
                'description': 'Bongkar muat armada Fuso 18 ton dari PT Wilmar lembur 3.5 jam',
                'hours': Decimal('3.50'),
                'recorded_by': created_users['gudang']
            }
        )

        self.stdout.write(self.style.SUCCESS("All demo dataset successfully updated & populated!"))
