# CV DHANA PUTRA MANDIRI - BACKEND API SPECIFICATION & INTEGRATION GUIDE

Backend API enterprise-grade untuk CV Dhana Putra Mandiri (distributor minyak goreng) dibangun menggunakan **Django 5.x / 6.x**, **Django REST Framework (DRF)**, dan **PostgreSQL 18**.

API ini dirancang untuk melayani **Next.js Frontend** yang *decoupled*, mencakup modul logistik gudang, akuntansi berpasangan (*double-entry*), kalkulasi Moving Average HPP otomatis, laporan keuangan (Neraca, Tahunan, Tren, Pie Chart), dan SDM/Payroll.

---

## 1. PANDUAN OTENTIKASI & ROLE PENGGUNA

### 1.1 Header Otentikasi
Gunakan header standar HTTP Authorization dengan Bearer Token:
```http
Authorization: Bearer <TOKEN>
```

### 1.2 Mode Demo & Development
Untuk kemudahan pengembangan dan prototyping di frontend Next.js, sistem mendukung token cepat tanpa harus login ke Keycloak/Auth0:
- `Bearer demo-direktur` -> Login sebagai Direktur (SuperAdmin)
- `Bearer demo-admin`    -> Login sebagai Admin (Penjualan & Keuangan)
- `Bearer demo-sales`    -> Login sebagai Sales
- `Bearer demo-gudang`   -> Login sebagai Gudang
- `Bearer demo-kasir`    -> Login sebagai Kasir (Finance)
- `Bearer demo-accounting` -> Login sebagai Accounting
- `Bearer demo-stakeholder` -> Login sebagai Stakeholder (Investor/Komisaris)

### 1.3 Kredensial Akun Bawaan (Database PostgreSQL)
| Username | Password | Role / Group | Deskripsi Hak Akses |
| :--- | :--- | :--- | :--- |
| `direktur` | `Direktur123!` | **Direktur** | **SuperAdmin** (Full CRUD) + Hak eksklusif tutup/buka periode akuntansi |
| `admin` | `Admin123!` | **Admin** | Gabungan transaksi Penjualan (Sales/Invoice) & Keuangan (Finance/Kasir) |
| `sales` | `Sales123!` | **Sales** | Draf Faktur, diskon. *Dilarang melihat HPP/Laba/Buku Besar; dilarang konfirmasi Surat Jalan.* |
| `gudang` | `Gudang123!` | **Gudang** | Konfirmasi Surat Jalan & Penerimaan Barang. *Nilai moneter (harga/HPP) otomatis disembunyikan.* |
| `kasir` | `Kasir123!` | **Finance** | Mutasi Kas & Bank, pembayaran invoice/supplier. *Dilarang ubah stok fisik.* |
| `accounting`| `Accounting123!` | **Accounting** | Validasi & posting Buku Besar (GL), Nota Debit, revisi nilai faktur short shipment |
| `stakeholder`| `Stakeholder123!` | **Stakeholder** | **Read-Only Dashboard** untuk melihat seluruh laporan keuangan & analitik |

---

## 2. MODUL INVENTORY & LOGISTIK (`/api/inventory/`)

### 2.1 Produk (Master Data Minyak Goreng)
- **`GET /api/inventory/products/`**: Daftar produk minyak goreng.
  * Catatan: Kolom `moving_average_hpp` dan `selling_price` otomatis di-*strip* (disembunyikan) untuk role Gudang. Kolom `moving_average_hpp` di-*strip* untuk role Sales.
- **`POST /api/inventory/products/`**: Tambah produk baru (wewenang Direktur / Admin).
- **`GET /api/inventory/products/abc-analysis/`**:
  * Melakukan kalkulasi Pareto/ABC berdasarkan nilai valuasi stok kumulatif:
    * **Kelas A**: 80% valuasi tertinggi
    * **Kelas B**: 15% berikutnya
    * **Kelas C**: 5% terendah
- **`GET /api/inventory/products/stock-estimation/`**:
  * Proyeksi ketahanan stok (runway days) terhadap ambang batas operasional 28 hari (`is_stock_below_28_days`).

### 2.2 Penerimaan Barang Masuk (`/api/inventory/goods-receipts/`)
- **`GET /api/inventory/goods-receipts/`**: Daftar penerimaan barang dari pabrik/supplier.
- **`POST /api/inventory/goods-receipts/`**: Input penerimaan barang baru. Format nomor otomatis: `GR/YYYYMM/XXXX`.
  ```json
  {
    "supplier_name": "PT Salim Ivomas Pratama Tbk",
    "po_reference": "PO-202611-0089",
    "receipt_date": "2026-11-10",
    "transport_cost": "1500000.00",
    "unloading_cost": "250000.00",
    "notes": "Penerimaan armada Fuso",
    "items": [
      {
        "product": 1,
        "qty_ordered": "100.00",
        "qty_actual": "100.00",
        "purchase_price": "212000.00"
      }
    ]
  }
  ```
- **`POST /api/inventory/goods-receipts/{id}/confirm/`**:
  * Konfirmasi fisik barang masuk oleh Gudang:
    1. Mengunci produk (`select_for_update`).
    2. Menambah kuantitas stok fisik.
    3. **Biaya Transport Supplier** diprorata dan diakumulasikan ke **Moving Average HPP**.
    4. **Ongkos Kuli Bongkar** dibukukan langsung ke Akun Beban Operasional (`COA 6100`), **tidak masuk HPP**.
    5. Jika `qty_actual < qty_ordered`, status otomatis ditandai `discrepancy_detected` dan pembayaran supplier diblokir.
    6. Otomatis membukukan jurnal berpasangan di Buku Besar.

### 2.3 Pengiriman Barang Keluar / Surat Jalan (`/api/inventory/deliveries/`)
- **`GET /api/inventory/deliveries/`**: Daftar surat jalan.
- **`POST /api/inventory/deliveries/`**: Buat surat jalan baru. Format nomor otomatis: `SJ/YYYYMM/XXXX`.
  ```json
  {
    "customer_name": "Toko Berkah Minyak Sejahtera",
    "delivery_date": "2026-11-10",
    "driver_name": "Joko Susanto",
    "vehicle_number": "B 9234 KDA",
    "sales_order_ref": "SO-202611-0042",
    "items": [
      {
        "product": 1,
        "qty": "30.00",
        "qty_delivered": "30.00"
      },
      {
        "product": 5,
        "qty": "50.00",
        "qty_delivered": "48.00"
      }
    ]
  }
  ```
- **`POST /api/inventory/deliveries/{id}/confirm/`**:
  * Konfirmasi keberangkatan barang fisik oleh Gudang (eksekusi atomik database):
    1. Mengunci stok produk via `select_for_update()`.
    2. Jika stok gudang kurang dari barang yang hendak dikirim, **transaksi di-rollback total dengan HTTP 409 Conflict**.
    3. Memotong stok fisik gudang **hanya sebesar kuantitas yang riil terkirim** (`qty_delivered`).
    4. Membukukan jurnal pengakuan Piutang & Pendapatan (`1130 Piutang` vs `4100 Pendapatan`) dan pengakuan HPP & Persediaan (`5100 HPP` vs `1140 Persediaan`).
    5. **Otomatis mencetak/merevisi Faktur Penjualan** yang hanya menagihkan jumlah barang yang berhasil terkirim.

---

## 3. MODUL KEUANGAN & AKUNTANSI (`/api/finance/`)

### 3.1 Bagan Akun (*Chart of Accounts*)
- **`GET /api/finance/chart-of-accounts/`**: Daftar akun COA (Kas, Bank BCA, Bank Mandiri, Piutang, Persediaan, Hutang, Modal, Pendapatan, HPP, Beban Bongkar, Beban Gaji, dll.).

### 3.2 Periode Akuntansi
- **`GET /api/finance/accounting-periods/`**: Daftar periode buku bulanan.
- **`POST /api/finance/accounting-periods/{id}/close_period/`**:
  * **Eksklusif Direktur**: Menutup buku periode akuntansi. Setelah ditutup, tidak ada transaksi yang boleh diposting ke tanggal periode ini.
- **`POST /api/finance/accounting-periods/{id}/reopen_period/`**:
  * **Eksklusif Direktur**: Membuka kembali periode akuntansi yang telah ditutup.

### 3.3 Buku Besar & Jurnal Voucher (`/api/finance/general-ledger/`)
- **`GET /api/finance/general-ledger/`**: Daftar jurnal transaksi (khusus Accounting, Finance, Admin, Direktur, Stakeholder).

### 3.4 Faktur Penjualan (`/api/finance/sales-invoices/`)
- **`GET /api/finance/sales-invoices/`**: Daftar faktur penjualan.
- **`POST /api/finance/sales-invoices/`**: Draf faktur penjualan baru. Format nomor otomatis: `INV/YYYYMM/XXXX`.

### 3.5 Nota Debit Supplier (`/api/finance/debit-notes/`)
- **`GET /api/finance/debit-notes/`**: Daftar nota debit.
- **`POST /api/finance/debit-notes/`**:
  * Diterbitkan oleh Accounting jika pengiriman supplier kurang (`Qty_Actual < Qty_Ordered`).
  * Mengurangi nilai Hutang Usaha (`COA 2110`) ke supplier dan mengoreksi persediaan.
  * Menghapus blokir pembayaran supplier sehingga sisa pembayaran yang sah dapat dicairkan oleh kasir.

### 3.6 Kas, Bank & Pembayaran (`/api/finance/payments/`)
- **`GET /api/finance/payments/`**: Mutasi kas dan bank.
- **`POST /api/finance/payments/`**:
  * Input pembayaran kas masuk (`BKM/YYYYMM/XXXX`) atau kas keluar (`BKK/YYYYMM/XXXX`).
  * Jika kategori `supplier_payment` dan barang masuk memiliki selisih yang belum diterbitkan Nota Debitnya, sistem menolak dan memblokir pembayaran secara otomatis.

---

## 4. MODUL LAPORAN KEUANGAN & ANALITIK DASHBOARD (`/api/finance/reports/`)

Semua endpoint ini dapat diakses oleh **Accounting**, **Finance**, **Admin**, **Direktur**, dan **Stakeholder**:

### 4.1 Laporan Neraca (*Balance Sheet*)
- **`GET /api/finance/reports/balance-sheet/?as_of_date=YYYY-MM-DD`**
- **Output:**
  ```json
  {
    "as_of_date": "2026-11-10",
    "assets": {
      "kas_dan_bank": {
        "kas_tunai": "10000000.00",
        "bank_bca": "75000000.00",
        "bank_mandiri": "50000000.00",
        "subtotal": "135000000.00"
      },
      "piutang_usaha": "25000000.00",
      "persediaan_barang_dagang": "180000000.00",
      "total_assets": "340000000.00"
    },
    "liabilities": {
      "hutang_usaha_supplier": "120000000.00",
      "hutang_gaji_upah": "0.00",
      "hutang_ongkos_bongkar": "1500000.00",
      "total_liabilities": "121500000.00"
    },
    "equity": {
      "modal_disetor": "150000000.00",
      "laba_ditahan": "40000000.00",
      "laba_periode_berjalan": "28500000.00",
      "total_equity": "218500000.00"
    },
    "summary": {
      "total_assets": "340000000.00",
      "total_liabilities_and_equity": "340000000.00",
      "difference": "0.00",
      "is_balanced": true
    }
  }
  ```

### 4.2 Laporan Penjualan Per Produk
- **`GET /api/finance/reports/product-sales/?year=2026`**
- Menyajikan per produk: SKU, Nama, Merek, Ukuran, Stok Sekarang, Qty Terjual, Total Omset, Total HPP, Laba Kotor, dan Persentase Margin Laba.

### 4.3 Grafik Tren Penjualan Bulanan (12 Bulan)
- **`GET /api/finance/reports/sales-trends/?year=2026`**
- Menyajikan data *time-series* dari Januari hingga Desember:
  `month`, `month_name`, `total_sales`, `total_volume`, `total_cogs`, `gross_profit`.

### 4.4 Laporan Tahunan (*Annual Report*)
- **`GET /api/finance/reports/annual-report/?year=2026`**
- Rangkuman fiskal 1 tahun penuh: Total Omset, Total HPP, Laba Kotor, Rincian Beban Operasional (Kuli Bongkar, Gaji, Armada, Umum), Laba Bersih Operasional, dan *Net Profit Margin %*.

### 4.5 Visualisasi Pie Chart Merek & Ukuran Kemasan
- **`GET /api/finance/reports/pie-charts/`**
- Format data teragregasi yang siap dipasang langsung ke Recharts / Chart.js di Next.js:
  - `brand_distribution`: `[{ "label": "Bimoli", "stock_value": 75250000, "stock_qty": 350, "percentage": 35.2 }, ...]`
  - `package_size_distribution`: `[{ "label": "2L", "stock_value": 145000000, "stock_qty": 680, "percentage": 65.5 }, ...]`

---

## 5. MODUL SDM & PAYROLL (`/api/hr/`)

### 5.1 Data Karyawan
- **`GET /api/hr/employees/`**: Daftar karyawan beserta riwayat mutasi dan catatan kinerja.
- **`POST /api/hr/employees/`**: Pendaftaran karyawan baru.

### 5.2 Mutasi Tenaga Kerja
- **`GET /api/hr/mutations/`**: Riwayat mutasi kerja.
- **`POST /api/hr/mutations/`**: Catat mutasi/promosi jabatan/kenaikan gaji.

### 5.3 Catatan Tenaga Kerja (*Labor Logs*)
- **`GET /api/hr/labor-records/`**: Buku log catatan absensi, jam lembur, insiden kerja gudang, dan apresiasi.
- **`POST /api/hr/labor-records/`**: Tambah catatan tenaga kerja baru.

### 5.4 Penggajian (*Payroll*)
- **`GET /api/hr/payroll-slips/`**: Daftar slip gaji.
- **`POST /api/hr/payroll-slips/generate/`**:
  * Buat draf slip gaji untuk karyawan di bulan & tahun tertentu:
    ```json
    {
      "employee": 1,
      "period_month": 11,
      "period_year": 2026,
      "overtime_allowance": "450000.00",
      "bonus_allowance": "200000.00",
      "deductions": "150000.00",
      "notes": "Lembur Fuso 3x"
    }
    ```
- **`POST /api/hr/payroll-slips/{id}/disburse/`**:
  * Menyetujui dan mencairkan gaji.
  * Otomatis membukukan jurnal pengeluaran ke Finance:
    * **Debit:** `6200 Beban Gaji & Upah Karyawan`
    * **Kredit:** `1120 Bank BCA` (atau `2120 Hutang Gaji`)

---

## 6. CARA MENJALANKAN DI DEVELOPMENT

1. **Jalankan Migrasi Database:**
   ```bash
   .\venv\Scripts\python manage.py migrate
   ```

2. **Inisialisasi Chart of Accounts & Role Permissions:**
   ```bash
   .\venv\Scripts\python manage.py seed_initial_data
   ```

3. **Inisialisasi Data Demo Lengkap (Produk, User, Transaksi, Laporan):**
   ```bash
   .\venv\Scripts\python manage.py seed_demo_data
   ```

4. **Jalankan Unit Test Suite:**
   ```bash
   .\venv\Scripts\python manage.py test
   ```

5. **Nyalakan Server Django API:**
   ```bash
   .\venv\Scripts\python manage.py runserver 0.0.0.0:8000
   ```
   * REST API: `http://localhost:8000/api/`
   * Django Admin: `http://localhost:8000/admin/`

