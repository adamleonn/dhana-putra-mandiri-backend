# CV Dhana Putra Mandiri - Backend API (Enterprise ERP)

Sistem backend Enterprise Resource Planning (ERP) untuk CV Dhana Putra Mandiri (distributor minyak goreng nasional) yang dibangun menggunakan **Django REST Framework** dan **PostgreSQL**.

API ini dirancang untuk melayani frontend modern yang terpisah (*decoupled* seperti Next.js), mengelola rantai pasok logistik minyak goreng, pembukuan berpasangan (*double-entry bookkeeping*), valuasi persediaan Moving Average HPP otomatis, kalkulasi penggajian SDM dua tahap, serta pelaporan keuangan eksekutif yang komprehensif.

---

## Fitur Utama Sistem

### 1. Modul Core (`/api/core/`)
- **Master Data Partner Bisnis** (`/api/core/customers/`, `/api/core/suppliers/`): Pengelolaan entitas Pelanggan dan Pemasok secara independen dengan validasi NPWP (`tax_id`), termin pembayaran (`payment_term_days`), dan *CheckConstraint* batas kredit (`credit_limit >= 0`).
- **Atomic Document Sequence Generator**: Penomoran dokumen transaksi anti-tabrakan (`SJ/YYYYMM/XXXX`, `INV/...`, `GR/...`, `PO/...`, `ND/...`, `BKM/...`, `BKK/...`, `JV/...`, `SLIP/...`) dengan *row-level locking* atomik (`select_for_update`).
- **OIDC-Ready Custom User Model**: Model pengguna terpusat (`core.User`) dengan dukungan federasi OpenID Connect (`oidc_issuer`, `oidc_subject`) dan *UniqueConstraint*.
- **Audit Logging Terpusat** (`/api/core/audit-logs/`): Pencatatan jejak audit mutasi data (aktor, aksi, model, IP address, request ID, perubahan *field*).

### 2. Modul Inventory & Logistik Gudang (`/api/inventory/`)
- **Master Data Produk Minyak Goreng**: Konversi multi-satuan (Karton, Jerigen, Botol ke Liter), batas stok minimum, valuasi total (`stock_value`), dan *runway* konsumsi harian (`daily_consumption_rate`).
- **Inbound Goods Receipt (Penerimaan Barang BPB)**:
  - Alokasi biaya pengiriman (*transport freight cost*) langsung dikapitalisasi ke kalkulasi Moving Average HPP produk.
  - Alokasi ongkos kuli bongkar muat langsung dibukukan ke Beban Operasional (COA 6100), tidak mempengaruhi HPP fisik barang.
  - Deteksi otomatis selisih barang kurang kirim (`Qty_Received < Qty_Ordered`) dengan status *shortage* yang mengunci pembayaran hutang supplier.
- **Outbound Delivery (Surat Jalan Pengiriman) - Invoice-First Flow**:
  - Draf Faktur Penjualan dibuat terlebih dahulu oleh Sales -> Draf Surat Jalan dibuat oleh Admin mengacu pada Faktur (`Delivery.sales_invoice` 1:1) -> Gudang mengonfirmasi pengiriman fisik atomik.
  - Pemotongan kuantitas stok gudang secara atomik dengan pengurutan ID produk (*sorted row locking*) untuk mencegah *deadlock*.
  - Proteksi stok fisik tidak mencukupi menghasilkan respons terstandarisasi *HTTP 409 Conflict*.
  - Penanganan *zero-delivered line*: baris barang yang batal dikirim dinilai dengan HPP = 0 tanpa pemotongan stok fisik.
- **Kartu Stok (Stock Movement Audit Trail)**: Tabel mutasi stok *append-only* (dilarang *update/delete*) dengan referensi bertipe ke penerimaan atau pengiriman barang.
- **Analisis Pareto ABC & Runway Estimasi**: Klasifikasi valuasi portofolio stok (Kelas A 80%, Kelas B 15%, Kelas C 5%) dan estimasi hari habis persediaan.

### 3. Modul Keuangan & Akuntansi (`/api/finance/`)
- **Bagan Akun (Chart of Accounts)**: Standar *double-entry bookkeeping* (Aktiva, Kewajiban, Modal, Pendapatan, HPP, Beban Operasional) dengan penanda akun kas/bank (`is_cash_bank`) dan akun yang dapat diposting (`is_postable`).
- **Buku Besar & Deferred Database Balance Trigger**:
  - Setiap transaksi operasional otomatis menerbitkan jurnal berimbang (*balanced double-entry*).
  - Dilindungi oleh **PostgreSQL Constraint Trigger** pada tingkat database (`check_journal_lines_balance_trigger`) yang secara otomatis menolak dan me-*rollback* transaksi apabila `Total Debit != Total Credit`.
- **Manajemen Periode Akuntansi (`AccountingPeriod`)**:
  - Menggunakan PostgreSQL extension `btree_gist` dengan *ExclusionConstraint* rentang tanggal (`daterange`) untuk mencegah periode fiskal saling tumpang tindih.
  - Hak eksklusif persetujuan tutup buku (*close period*) berada di tangan Direktur. Periode yang tertutup memblokir seluruh mutasi jurnal baru.
- **Nota Debit Supplier (Debit Note)**: Fasilitas Accounting untuk memotong Hutang Dagang atas barang supplier yang kurang kirim dan membuka blokir pencairan pembayaran kasir.
- **Kas & Bank (Payment Services)**:
  - Pembayaran Pelanggan (BKM / *customer receipt*).
  - Pembayaran Hutang Supplier (BKK / *supplier payment*) dengan validasi pengurang Nota Debit.
  - Pencairan Gaji Karyawan (Payroll BKK).
- **Laporan Keuangan Eksekutif**:
  - Neraca Keuangan (*Balance Sheet*) otomatis seimbang.
  - Laporan Keuangan Tahunan (*Comprehensive Annual Statement*).
  - Grafik Tren Penjualan 12 Bulan.
  - Analisis Distribusi Penjualan berdasarkan Merek & Kemasan.

### 4. Modul SDM & Penggajian (`/api/hr/`)
- **Master Karyawan & Riwayat Mutasi**: Pelacakan promosi, mutasi divisi, penyesuaian gaji pokok, nomor identitas KTP (`national_id`), dan NPWP (`tax_id`).
- **Penyaringan Data Sensitif (*Role Masking*)**: Informasi gaji pokok, tunjangan, nomor rekening, dan NIK otomatis disembunyikan/dihapus (*masked*) untuk peran non-Direktur.
- **Catatan Tenaga Kerja (`LaborRecord`)**: Pencatatan log lembur armada/kuli bongkar muat, catatan kehadiran, surat peringatan, dan insiden lapangan.
- **Kalkulasi Gaji Bulanan Dua Tahap (*Two-Stage Payroll*)**:
  1. *Generation & Approval*: Pembuatan slip gaji bulanan (`/api/hr/payroll-slips/generate_monthly/`) dan persetujuan Direktur yang otomatis menerbitkan jurnal akrual hutang gaji.
  2. *Disbursement*: Pembayaran kas/bank oleh Finance yang menutup hutang gaji dan menerbitkan BKK kas keluar.

### 5. Keamanan & Performa Arsitektur
- **Nol `FloatField`**: Seluruh nilai moneter dan kuantitas menggunakan `DecimalField(max_digits=15, decimal_places=2)`.
- **Integritas Relasi**: Seluruh *Foreign Key* pengguna transaksional menggunakan `on_delete=models.PROTECT`.
- **Role-Aware Serializers (`RoleFilteredSerializerMixin`)**: Otomatis menyaring dan menghapus field harga/moneter untuk peran Gudang, serta menghapus HPP/margin untuk peran Sales dan Admin Operasional.
- **OpenAPI & Dokumentasi Interaktif**: Ditenagai oleh `drf-spectacular` di `/api/schema/swagger-ui/` dan `/api/schema/redoc/`.

---

## Struktur Role Pengguna

| Username | Role / Group | Hak Akses Utama |
| :--- | :--- | :--- |
| `direktur` | **Direktur** | **SuperAdmin** (Akses penuh CRUD + Hak eksklusif tutup/buka periode akuntansi) |
| `admin` | **Admin** | Gabungan transaksi Penjualan (Sales/Invoice) & Keuangan (Finance/Kasir) |
| `sales` | **Sales** | Draf Faktur, Surat Jalan, Diskon. *Nilai HPP dan Buku Besar disembunyikan.* |
| `gudang` | **Gudang** | Konfirmasi Surat Jalan & Penerimaan Barang. *Nilai moneter otomatis disembunyikan.* |
| `kasir` | **Finance** | Mutasi Kas & Bank, pembayaran supplier. *Dilarang merubah stok fisik.* |
| `accounting` | **Accounting** | Buku Besar, Nota Debit, revisi nilai faktur, pengajuan tutup buku. |
| `stakeholder` | **Stakeholder** | **Read-Only Dashboard** untuk melihat seluruh laporan keuangan & analitik. |

---

### Matriks Hubungan Role dengan 4 Modul

| Role | 1. Modul Core (Pelanggan, Supplier, Counter) | 2. Modul Inventory (Logistik Gudang & Stok) | 3. Modul Finance (Keuangan, Faktur, Jurnal) | 4. Modul HR (Karyawan & Payroll) |
| :--- | :--- | :--- | :--- | :--- |
| **Direktur** | **Full CRUD**: Kontrol penuh data partner bisnis & konfigurasi sistem. | **Full CRUD**: Otorisasi penghapusan stok, penyesuaian opname khusus. | **Hak Eksklusif**: Menyetujui **Tutup / Buka Periode Akuntansi**, akses seluruh laporan keuangan. | **Otorisasi**: Menyetujui mutasi/promosi, otorisasi pencairan gaji bulanan. |
| **Stakeholder** | **Read-Only**: Melihat daftar profil rekanan. | **Read-Only**: Melihat ketahanan stok & Pareto ABC. | **Read-Only Dashboard**: Memantau Neraca, Laba-Rugi, Tren Penjualan 12 Bulan, & Pie Chart. | **Read-Only**: Melihat struktur organisasi & total beban upah. |
| **Accounting** | **Read**: Memvalidasi identitas legal supplier & pelanggan. | **Read**: Memantau HPP Moving Average, Kartu Stok, dan audit selisih kirim. | **Main Control**: Mengaudit Buku Besar (GL), menerbitkan **Nota Debit** (potong hutang supplier), revisi faktur. | **Audit**: Memeriksa jurnal otomatis atas beban gaji karyawan. |
| **Admin** | **CRUD**: Menambah dan mengupdate data pelanggan & supplier baru. | **Read / Create**: Menyiapkan draf dokumen jalan & penerimaan. | **Operasional**: Membuat faktur penjualan, mencatat penerimaan/pembayaran rutin. | **Read / Update**: Mengelola biodata karyawan operasional. |
| **Sales** | **Read**: Mengakses daftar pelanggan untuk penawaran. | **Restricted**: Melihat ketersediaan stok fisik. **HPP disembunyikan total** guna melindungi margin. | **Create Draft**: Membuat draf Faktur & diskon promo. Dilarang melihat Buku Besar. | Tidak ada akses. |
| **Gudang** | **Read**: Alamat tujuan kirim & asal supplier. | **Main Control**: Konfirmasi fisik barang masuk (BPB) & keluar (Surat Jalan). **Harga/HPP disembunyikan total**. | Tidak ada akses finansial (semua nominal rupiah otomatis disaring oleh serializer). | **Input**: Mencatat log lembur harian kuli bongkar muat armada. |
| **Kasir / Finance** | **Read**: Rekening bank supplier & plafon kredit pelanggan. | Tidak ada akses mengubah stok fisik. | **Main Control**: Memproses Bukti Kas Masuk (BKM) dan Bukti Kas Keluar (BKK). | **Eksekusi**: Mencairkan transfer gaji bersih karyawan setelah di-approve Direktur. |

---

## Panduan Integrasi Frontend (Next.js / React)

Backend menyediakan fasilitas integrasi cepat untuk tim Frontend:

### 1. Header Otentikasi Cepat (Demo Mode)
Gunakan header HTTP Authorization standar:
```http
Authorization: Bearer <TOKEN>
```
Token pengembangan bawaan:
- `Bearer demo-direktur` -> Hak akses penuh SuperAdmin
- `Bearer demo-admin` -> Hak akses tim Operasional Admin
- `Bearer demo-sales` -> Hak akses tim Sales
- `Bearer demo-gudang` -> Hak akses operasional Gudang
- `Bearer demo-kasir` -> Hak akses Kasir / Keuangan
- `Bearer demo-accounting` -> Hak akses pembukuan Accounting
- `Bearer demo-stakeholder` -> Hak akses Read-Only Dashboard

### 2. Penanganan Error Standar
- **HTTP 409 Conflict (Stok Kurang)**:
  ```json
  {
    "code": "INSUFFICIENT_STOCK",
    "message": "Stok tidak mencukupi untuk SKU MNK-BIM-2L-12. Permintaan: 500.00, Stok Tersedia: 100.00.",
    "details": {
      "sku": "MNK-BIM-2L-12",
      "product_name": "Bimoli Spesial 2L",
      "requested_qty": "500.00",
      "available_stock": "100.00"
    }
  }
  ```
- **HTTP 423 Locked (Periode Tertutup)**:
  Terjadi ketika mencoba mencatat atau mengubah jurnal pada periode buku yang sudah ditutup.
- **HTTP 403 Forbidden**: Terjadi jika pengguna mengakses endpoint atau tindakan di luar wewenang rolenya.

---

## Panduan Instalasi & Menjalankan Proyek

### 1. Kloning Repository
```bash
git clone https://github.com/adamleonn/dhana-putra-mandiri-backend.git
cd dhana-putra-mandiri-backend
```

### 2. Konfigurasi Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Instal Dependensi
```bash
pip install django djangorestframework psycopg2-binary django-cors-headers python-dotenv joserfc cryptography drf-spectacular django-filter
```

### 4. Konfigurasi Environment Variable
Salin template konfigurasi:
```bash
cp .env.example .env
```
Sesuaikan parameter koneksi database PostgreSQL pada file `.env`.

### 5. Buat Database PostgreSQL
Pastikan service PostgreSQL telah berjalan, dan jangan lupa untuk membuat database PostgreSQL terlebih dahulu sebelum menjalankan migrasi:
```sql
CREATE DATABASE dhana_putra_mandiri_dev;
```
*(Sesuaikan nama database dengan variabel `DB_NAME` yang Anda konfigurasi di file `.env`)*.

### 6. Jalankan Migrasi Database
```bash
python manage.py migrate
```

### 7. Seeding Data Role & Data Demo Awal
Jalankan perintah berikut untuk menginisialisasi grup RBAC, akun COA, master data produk, karyawan, dan seluruh demo user:
```bash
python manage.py seed_groups_and_roles
python manage.py seed_initial_data
python manage.py seed_demo_data
```

### 8. Jalankan Unit & Concurrency Test
```bash
python manage.py test
```

### 9. Regenerasi Dokumentasi ERD & Kamus Data
Jalankan perintah berikut untuk meregenerasi diagram ERD Mermaid (`docs/erd.mmd`) dan kamus data (`docs/data_dictionary.md`):
```bash
python manage.py generate_docs
```

### 10. Jalankan Server Development
```bash
python manage.py runserver 0.0.0.0:8000
```
Akses Swagger UI di: [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)

---

## Pengujian API Menggunakan Postman
File Postman Collection dan Environment telah disertakan pada root repository:
- `postman_collection.json`: Berisi skenario uji komprehensif (Master Data, Inbound BPB, Draf Faktur, Outbound SJ, Konfirmasi Fisik Gudang, Pembayaran Kasir, Buku Besar, Neraca, Payroll Dua Tahap, dan Uji Keamanan 403 Forbidden).
- `postman_environment.json`: Variabel lingkungan `baseUrl` dan demo bearer token untuk ke-7 role.

Anda dapat mengimpor kedua file tersebut ke Postman atau menjalankannya langsung melalui Newman CLI:
```bash
newman run postman_collection.json -e postman_environment.json
```
