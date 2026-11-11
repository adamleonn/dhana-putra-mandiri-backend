import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models


class Command(BaseCommand):
    help = "Generates docs/erd.mmd and docs/data_dictionary.md from Django models metadata."

    def handle(self, *args, **options):
        self.stdout.write("Generating docs/erd.mmd...")
        self.generate_erd()
        self.stdout.write("Generating docs/data_dictionary.md...")
        self.generate_data_dictionary()
        self.stdout.write(self.style.SUCCESS("Documentation successfully generated."))

    def generate_erd(self):
        content = """```mermaid
erDiagram
  %% Core & Identity Relations
  USER ||--o{ AUDIT_LOG : "performs (actor)"
  USER ||--o| EMPLOYEE : "profile (user)"
  USER ||--o{ PURCHASE_ORDER : "creates (created_by)"
  USER ||--o{ GOODS_RECEIPT : "confirms (confirmed_by)"
  USER ||--o{ DELIVERY : "confirms (confirmed_by)"
  USER ||--o{ SALES_INVOICE : "creates (created_by)"
  USER ||--o{ GENERAL_LEDGER : "posts (posted_by)"
  USER ||--o{ PAYROLL_SLIP : "approves (approved_by)"

  %% Customer & Supplier
  CUSTOMER ||--o{ SALES_INVOICE : "billed (customer)"
  CUSTOMER ||--o{ DELIVERY : "receives (customer)"
  SUPPLIER ||--o{ PURCHASE_ORDER : "ordered from (supplier)"
  SUPPLIER ||--o{ GOODS_RECEIPT : "supplies (supplier)"
  SUPPLIER ||--o{ DEBIT_NOTE : "charged (supplier)"

  %% Products & Catalog
  PRODUCT ||--o{ PRODUCT_PRICE_TIER : "priced by"
  PRODUCT ||--o{ PURCHASE_ORDER_ITEM : "ordered"
  PRODUCT ||--o{ GOODS_RECEIPT_ITEM : "received"
  PRODUCT ||--o{ SALES_INVOICE_ITEM : "billed"
  PRODUCT ||--o{ DELIVERY_ITEM : "dispatched"
  PRODUCT ||--o{ STOCK_MOVEMENT : "tracked"

  %% Purchasing & Inbound Inventory
  PURCHASE_ORDER ||--|{ PURCHASE_ORDER_ITEM : "has"
  PURCHASE_ORDER ||--o{ GOODS_RECEIPT : "fulfilled by"
  GOODS_RECEIPT ||--|{ GOODS_RECEIPT_ITEM : "has"
  GOODS_RECEIPT ||--o{ DEBIT_NOTE : "discrepancy"
  GOODS_RECEIPT ||--o{ PAYMENT : "settled by"
  GOODS_RECEIPT_ITEM ||--o| STOCK_MOVEMENT : "creates IN"

  %% Sales, Outbound Delivery & Inventory
  SALES_INVOICE ||--|{ SALES_INVOICE_ITEM : "has"
  SALES_INVOICE ||--o{ SALES_INVOICE_REVISION : "revised"
  SALES_INVOICE ||--|| DELIVERY : "fulfilled by (Delivery.sales_invoice 1:1)"
  SALES_INVOICE ||--o{ PAYMENT : "paid by"
  DELIVERY ||--|{ DELIVERY_ITEM : "has"
  SALES_INVOICE_ITEM ||--o| DELIVERY_ITEM : "delivered as"
  DELIVERY_ITEM ||--o| STOCK_MOVEMENT : "creates OUT"

  %% General Ledger & Cash/Bank
  DEBIT_NOTE ||--o{ PAYMENT : "offsets"
  CHART_OF_ACCOUNTS ||--o{ PAYMENT : "cash_bank_account"
  CHART_OF_ACCOUNTS ||--o{ GENERAL_LEDGER_LINE : "posted to"
  CHART_OF_ACCOUNTS ||--o| CHART_OF_ACCOUNTS : "parent"
  ACCOUNTING_PERIOD ||--o{ GENERAL_LEDGER : "includes"
  GENERAL_LEDGER ||--|{ GENERAL_LEDGER_LINE : "has lines"
  GENERAL_LEDGER ||--o| GENERAL_LEDGER : "reversal_of"
  GENERAL_LEDGER ||--o{ SALES_INVOICE : "journal"
  GENERAL_LEDGER ||--o{ DEBIT_NOTE : "journal"
  GENERAL_LEDGER ||--o{ PAYMENT : "journal / reversal"

  %% Human Resources & Payroll
  EMPLOYEE ||--o{ EMPLOYEE_MUTATION : "history"
  EMPLOYEE ||--o{ LABOR_RECORD : "logs"
  EMPLOYEE ||--o{ PAYROLL_SLIP : "receives"
  PAYROLL_SLIP ||--o| PAYMENT : "paid by (category payroll)"
  GENERAL_LEDGER ||--o{ PAYROLL_SLIP : "accrual journal"

  %% Document Sequence Tracking
  DOCUMENT_SEQUENCE_COUNTER {
    string doc_type PK
    string period_key PK
    int last_number
  }

  USER {
    int id PK
    string username UK
    string email
    string oidc_issuer
    string oidc_subject UK
    boolean is_active
  }

  CUSTOMER {
    int id PK
    string code UK
    string name
    string tax_id
    decimal credit_limit
    int payment_term_days
  }

  SUPPLIER {
    int id PK
    string code UK
    string name
    string tax_id
    int payment_term_days
  }

  PRODUCT {
    int id PK
    string sku UK
    string name
    string category
    string brand
    decimal physical_stock
    decimal stock_value
    decimal current_hpp
    decimal selling_price
    string abc_class
  }

  GOODS_RECEIPT {
    int id PK
    string receipt_number UK
    int supplier_id FK
    date receipt_date
    decimal transport_cost
    decimal unloading_cost
    decimal total_amount
    decimal payable_amount
    decimal debit_note_total
    decimal paid_amount
    string status
  }

  SALES_INVOICE {
    int id PK
    string invoice_number UK
    int customer_id FK
    date invoice_date
    date due_date
    decimal total_amount
    decimal paid_amount
    string status
  }

  DELIVERY {
    int id PK
    string delivery_number UK
    int sales_invoice_id FK "1:1"
    int customer_id FK
    date delivery_date
    string driver_name
    string vehicle_number
    string status
  }

  GENERAL_LEDGER {
    int id PK
    string journal_number UK
    int period_id FK
    date transaction_date
    string source_document
    int reversal_of_id FK
    boolean is_posted
  }

  PAYMENT {
    int id PK
    string payment_number UK
    string payment_method
    string category
    string direction
    int cash_bank_account_id FK
    int sales_invoice_id FK
    int goods_receipt_id FK
    int payroll_slip_id FK
    decimal amount
    date payment_date
  }
```
"""
        os.makedirs("docs", exist_ok=True)
        with open(os.path.join("docs", "erd.mmd"), "w", encoding="utf-8") as f:
            f.write(content)

    def generate_data_dictionary(self):
        target_apps = ["core", "inventory", "finance", "hr"]
        lines = []
        lines.append("# Data Dictionary - CV Dhana Putra Mandiri Mini-ERP")
        lines.append("\nDokumen ini menjelaskan seluruh tabel, kolom, tipe data, fungsi bisnis, dan aturan visibilitas berbasis peran (Role-Based Visibility) pada sistem ERP CV Dhana Putra Mandiri.\n")

        lines.append("## Matriks Hak Akses & Pembatasan Role")
        lines.append("| Role | Moneter / Harga Beli (HPP) | Harga Jual | Stok Fisik | Jurnal Umum | Gaji / Data Sensitif HR | Tutup Periode |")
        lines.append("|---|---|---|---|---|---|---|")
        lines.append("| **Direktur** | Full Akses | Full Akses | Full Akses | Full Akses | Full Akses | Eksklusif |")
        lines.append("| **Admin** | **Hidden** | Akses | Akses | **Hidden** | **Masked** | Dilarang |")
        lines.append("| **Sales** | **Hidden** | Akses | Akses (Read) | **Hidden** | Dilarang | Dilarang |")
        lines.append("| **Gudang** | **Hidden** | **Hidden** | Akses Penuh | **Hidden** | Dilarang | Dilarang |")
        lines.append("| **Finance** | Akses | Akses | **Read-Only** | Akses (Kas/Bank) | **Masked** | Dilarang |")
        lines.append("| **Accounting** | Akses Penuh | Akses Penuh | Read-Only | Akses Penuh | **Masked** | Rekomendasi saja |")
        lines.append("| **Stakeholder** | Read-Only | Read-Only | Read-Only | Read-Only | **Masked** | Dilarang |")
        lines.append("\n---\n")

        for app_label in target_apps:
            app_config = apps.get_app_config(app_label)
            lines.append(f"## Modul: {app_label.upper()}\n")

            for model in app_config.get_models():
                table_name = model._meta.db_table
                model_name = model.__name__
                doc = model.__doc__ or "Tidak ada dokumentasi khusus."
                doc = doc.strip().split("\n")[0]

                lines.append(f"### {model_name} (`{table_name}`)")
                lines.append(f"**Deskripsi:** {doc}\n")
                lines.append("| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |")
                lines.append("|---|---|---|---|---|")

                for field in model._meta.fields:
                    col_name = field.column or field.name
                    f_type = field.get_internal_type()
                    null_str = "Null" if field.null else ("Blank" if field.blank else "Wajib (Required)")
                    help_txt = field.help_text or getattr(field, 'verbose_name', col_name)

                    # Determine role visibility based on column name & model
                    if col_name in ['current_hpp', 'stock_value', 'hpp_at_delivery', 'total_cogs', 'allocated_transport_cost', 'allocated_unloading_cost', 'effective_unit_cost']:
                        visibility = "Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang)"
                    elif col_name in ['base_salary', 'standard_allowance', 'bank_account_number', 'national_id', 'previous_salary', 'new_salary']:
                        visibility = "Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting)"
                    elif col_name in ['selling_price', 'total_amount', 'subtotal', 'discount_amount', 'paid_amount', 'payable_amount', 'amount', 'credit_limit']:
                        visibility = "Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter)"
                    else:
                        visibility = "Publik / Sesuai Izin Modul"

                    lines.append(f"| `{col_name}` | {f_type} | {null_str} | {help_txt} | {visibility} |")
                lines.append("\n")

        with open(os.path.join("docs", "data_dictionary.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
