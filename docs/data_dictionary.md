# Data Dictionary - CV Dhana Putra Mandiri Mini-ERP

Dokumen ini menjelaskan seluruh tabel, kolom, tipe data, fungsi bisnis, dan aturan visibilitas berbasis peran (Role-Based Visibility) pada sistem ERP CV Dhana Putra Mandiri.

## Matriks Hak Akses & Pembatasan Role
| Role | Moneter / Harga Beli (HPP) | Harga Jual | Stok Fisik | Jurnal Umum | Gaji / Data Sensitif HR | Tutup Periode |
|---|---|---|---|---|---|---|
| **Direktur** | Full Akses | Full Akses | Full Akses | Full Akses | Full Akses | Eksklusif |
| **Admin** | **Hidden** | Akses | Akses | **Hidden** | **Masked** | Dilarang |
| **Sales** | **Hidden** | Akses | Akses (Read) | **Hidden** | Dilarang | Dilarang |
| **Gudang** | **Hidden** | **Hidden** | Akses Penuh | **Hidden** | Dilarang | Dilarang |
| **Finance** | Akses | Akses | **Read-Only** | Akses (Kas/Bank) | **Masked** | Dilarang |
| **Accounting** | Akses Penuh | Akses Penuh | Read-Only | Akses Penuh | **Masked** | Rekomendasi saja |
| **Stakeholder** | Read-Only | Read-Only | Read-Only | Read-Only | **Masked** | Dilarang |

---

## Modul: CORE

### User (`core_user`)
**Deskripsi:** User(id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, oidc_issuer, oidc_subject)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `password` | CharField | Wajib (Required) | sandi | Publik / Sesuai Izin Modul |
| `last_login` | DateTimeField | Null | masuk terakhir | Publik / Sesuai Izin Modul |
| `is_superuser` | BooleanField | Wajib (Required) | Menentukan apakah pengguna memiliki semua hak akses tanpa perlu diberikan secara manual. | Publik / Sesuai Izin Modul |
| `username` | CharField | Wajib (Required) | Wajib. 150 karakter atau sedikit. Hanya huruf, angka, dan @/./+/-/_. | Publik / Sesuai Izin Modul |
| `first_name` | CharField | Blank | nama depan | Publik / Sesuai Izin Modul |
| `last_name` | CharField | Blank | nama belakang | Publik / Sesuai Izin Modul |
| `email` | CharField | Blank | alamat email | Publik / Sesuai Izin Modul |
| `is_staff` | BooleanField | Wajib (Required) | Menentukan apakah pengguna berhak masuk ke situs administrasi ini. | Publik / Sesuai Izin Modul |
| `is_active` | BooleanField | Wajib (Required) | Menentukan apakah pengguna dianggap aktif. Hapus pilihan ini tanpa perlu menghapus akunnya. | Publik / Sesuai Izin Modul |
| `date_joined` | DateTimeField | Wajib (Required) | tanggal daftar | Publik / Sesuai Izin Modul |
| `oidc_issuer` | CharField | Null | OIDC Issuer URL (Identity Provider) | Publik / Sesuai Izin Modul |
| `oidc_subject` | CharField | Null | OIDC Subject Identifier (sub) | Publik / Sesuai Izin Modul |


### DocumentSequenceCounter (`core_documentsequencecounter`)
**Deskripsi:** DocumentSequenceCounter(id, doc_type, period_key, last_number, updated_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `doc_type` | CharField | Wajib (Required) | doc type | Publik / Sesuai Izin Modul |
| `period_key` | CharField | Wajib (Required) | period key | Publik / Sesuai Izin Modul |
| `last_number` | PositiveIntegerField | Wajib (Required) | last number | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |


### Customer (`core_customer`)
**Deskripsi:** Customer(id, created_at, updated_at, code, name, tax_id, contact_person, phone, email, address, credit_limit, payment_term_days, is_active)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `code` | CharField | Wajib (Required) | code | Publik / Sesuai Izin Modul |
| `name` | CharField | Wajib (Required) | name | Publik / Sesuai Izin Modul |
| `tax_id` | CharField | Blank | NPWP Pelanggan | Publik / Sesuai Izin Modul |
| `contact_person` | CharField | Blank | contact person | Publik / Sesuai Izin Modul |
| `phone` | CharField | Blank | phone | Publik / Sesuai Izin Modul |
| `email` | CharField | Blank | email | Publik / Sesuai Izin Modul |
| `address` | TextField | Blank | address | Publik / Sesuai Izin Modul |
| `credit_limit` | DecimalField | Wajib (Required) | Batas plafon kredit piutang (IDR) | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `payment_term_days` | PositiveIntegerField | Wajib (Required) | Termin jatuh tempo pembayaran dalam hari (TOP) | Publik / Sesuai Izin Modul |
| `is_active` | BooleanField | Wajib (Required) | is active | Publik / Sesuai Izin Modul |


### Supplier (`core_supplier`)
**Deskripsi:** Supplier(id, created_at, updated_at, code, name, tax_id, contact_person, phone, email, address, payment_term_days, is_active)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `code` | CharField | Wajib (Required) | code | Publik / Sesuai Izin Modul |
| `name` | CharField | Wajib (Required) | name | Publik / Sesuai Izin Modul |
| `tax_id` | CharField | Blank | NPWP Supplier | Publik / Sesuai Izin Modul |
| `contact_person` | CharField | Blank | contact person | Publik / Sesuai Izin Modul |
| `phone` | CharField | Blank | phone | Publik / Sesuai Izin Modul |
| `email` | CharField | Blank | email | Publik / Sesuai Izin Modul |
| `address` | TextField | Blank | address | Publik / Sesuai Izin Modul |
| `payment_term_days` | PositiveIntegerField | Wajib (Required) | Termin pembayaran hutang dagang dalam hari | Publik / Sesuai Izin Modul |
| `is_active` | BooleanField | Wajib (Required) | is active | Publik / Sesuai Izin Modul |


### AuditLog (`core_auditlog`)
**Deskripsi:** AuditLog(id, actor, action, model_name, object_id, object_repr, changes, ip_address, request_id, created_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `actor_id` | ForeignKey | Null | Pengguna yang melakukan aksi | Publik / Sesuai Izin Modul |
| `action` | CharField | Wajib (Required) | action | Publik / Sesuai Izin Modul |
| `model_name` | CharField | Wajib (Required) | model name | Publik / Sesuai Izin Modul |
| `object_id` | CharField | Wajib (Required) | object id | Publik / Sesuai Izin Modul |
| `object_repr` | CharField | Blank | object repr | Publik / Sesuai Izin Modul |
| `changes` | JSONField | Blank | changes | Publik / Sesuai Izin Modul |
| `ip_address` | GenericIPAddressField | Null | ip address | Publik / Sesuai Izin Modul |
| `request_id` | CharField | Blank | request id | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |


## Modul: INVENTORY

### Product (`inventory_product`)
**Deskripsi:** Product(id, created_at, updated_at, created_by, updated_by, sku, name, description, uom, base_unit, conversion_factor, current_stock, stock_value, moving_average_hpp, selling_price, brand, package_size, lead_time_days, abc_class, daily_consumption_rate, min_stock_level, is_active)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `sku` | CharField | Wajib (Required) | sku | Publik / Sesuai Izin Modul |
| `name` | CharField | Wajib (Required) | name | Publik / Sesuai Izin Modul |
| `description` | TextField | Blank | description | Publik / Sesuai Izin Modul |
| `uom` | CharField | Wajib (Required) | Unit of Measure transaksi penjualan/pembelian | Publik / Sesuai Izin Modul |
| `base_unit` | CharField | Wajib (Required) | Satuan dasar inventory terkecil (misal: Liter, Kg, Pcs) | Publik / Sesuai Izin Modul |
| `conversion_factor` | DecimalField | Wajib (Required) | Faktor pengali UOM ke base_unit (Contoh: 1 Karton 2L isi 6 = 12.00 Liter) | Publik / Sesuai Izin Modul |
| `current_stock` | DecimalField | Wajib (Required) | Kuantitas stok fisik di gudang saat ini (dalam satuan UOM) | Publik / Sesuai Izin Modul |
| `stock_value` | DecimalField | Wajib (Required) | Total nilai rupiah persediaan (stock_value = current_stock * moving_average_hpp) | Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang) |
| `moving_average_hpp` | DecimalField | Wajib (Required) | Harga Pokok Penjualan Moving Average per UOM | Publik / Sesuai Izin Modul |
| `selling_price` | DecimalField | Wajib (Required) | Harga jual dasar standar (IDR) | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `brand` | CharField | Blank | brand | Publik / Sesuai Izin Modul |
| `package_size` | CharField | Blank | Contoh: 2 Liter, 1 Liter, 5 Liter | Publik / Sesuai Izin Modul |
| `lead_time_days` | PositiveIntegerField | Wajib (Required) | Estimasi waktu tunggu pemesanan ulang dari supplier (hari) | Publik / Sesuai Izin Modul |
| `abc_class` | CharField | Wajib (Required) | Klasifikasi Pareto ABC yang dihitung berkala oleh batch job | Publik / Sesuai Izin Modul |
| `daily_consumption_rate` | DecimalField | Wajib (Required) | Estimasi konsumsi harian UOM yang dihitung oleh batch job | Publik / Sesuai Izin Modul |
| `min_stock_level` | DecimalField | Wajib (Required) | Batas minimum stok aman gudang (Safety Stock) | Publik / Sesuai Izin Modul |
| `is_active` | BooleanField | Wajib (Required) | is active | Publik / Sesuai Izin Modul |


### ProductPriceTier (`inventory_productpricetier`)
**Deskripsi:** ProductPriceTier(id, product, min_qty, price, effective_from)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `product_id` | ForeignKey | Wajib (Required) | product | Publik / Sesuai Izin Modul |
| `min_qty` | DecimalField | Wajib (Required) | Kuantitas minimal order untuk mendapatkan harga tier ini | Publik / Sesuai Izin Modul |
| `price` | DecimalField | Wajib (Required) | Harga jual per unit pada tier ini | Publik / Sesuai Izin Modul |
| `effective_from` | DateField | Wajib (Required) | effective from | Publik / Sesuai Izin Modul |


### PurchaseOrder (`inventory_purchaseorder`)
**Deskripsi:** PurchaseOrder(id, created_at, updated_at, created_by, updated_by, po_number, supplier, order_date, status, notes)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `po_number` | CharField | Wajib (Required) | po number | Publik / Sesuai Izin Modul |
| `supplier_id` | ForeignKey | Wajib (Required) | supplier | Publik / Sesuai Izin Modul |
| `order_date` | DateField | Wajib (Required) | order date | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |


### PurchaseOrderItem (`inventory_purchaseorderitem`)
**Deskripsi:** PurchaseOrderItem(id, purchase_order, product, qty_ordered, unit_price, line_total)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `purchase_order_id` | ForeignKey | Wajib (Required) | purchase order | Publik / Sesuai Izin Modul |
| `product_id` | ForeignKey | Wajib (Required) | product | Publik / Sesuai Izin Modul |
| `qty_ordered` | DecimalField | Wajib (Required) | qty ordered | Publik / Sesuai Izin Modul |
| `unit_price` | DecimalField | Wajib (Required) | unit price | Publik / Sesuai Izin Modul |
| `line_total` | DecimalField | Wajib (Required) | line total | Publik / Sesuai Izin Modul |


### GoodsReceipt (`inventory_goodsreceipt`)
**Deskripsi:** GoodsReceipt(id, created_at, updated_at, created_by, updated_by, receipt_number, purchase_order, supplier, supplier_name_snapshot, receipt_date, due_date, payment_method, payment_status, transport_cost, unloading_cost, payable_amount, debit_note_total, paid_amount, accounting_period, status, notes, received_by, confirmed_by, confirmed_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `receipt_number` | CharField | Wajib (Required) | receipt number | Publik / Sesuai Izin Modul |
| `purchase_order_id` | ForeignKey | Null | purchase order | Publik / Sesuai Izin Modul |
| `supplier_id` | ForeignKey | Wajib (Required) | supplier | Publik / Sesuai Izin Modul |
| `supplier_name_snapshot` | CharField | Blank | supplier name snapshot | Publik / Sesuai Izin Modul |
| `receipt_date` | DateField | Wajib (Required) | receipt date | Publik / Sesuai Izin Modul |
| `due_date` | DateField | Null | due date | Publik / Sesuai Izin Modul |
| `payment_method` | CharField | Wajib (Required) | payment method | Publik / Sesuai Izin Modul |
| `payment_status` | CharField | Wajib (Required) | payment status | Publik / Sesuai Izin Modul |
| `transport_cost` | DecimalField | Wajib (Required) | Ongkos kirim masuk yang DIALOKASIKAN ke HPP produk | Publik / Sesuai Izin Modul |
| `unloading_cost` | DecimalField | Wajib (Required) | Biaya kuli bongkar muat - TIDAK MASUK HPP, langsung dicatat sebagai beban operasional | Publik / Sesuai Izin Modul |
| `payable_amount` | DecimalField | Wajib (Required) | Total hutang supplier (Nilai Barang Aktual + Ongkir Masuk jika ditagihkan) | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `debit_note_total` | DecimalField | Wajib (Required) | Akumulasi potongan klaim Nota Debit atas kekurangan fisik barang | Publik / Sesuai Izin Modul |
| `paid_amount` | DecimalField | Wajib (Required) | Jumlah pembayaran yang telah diselesaikan ke supplier | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `accounting_period_id` | ForeignKey | Null | accounting period | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |
| `received_by_id` | ForeignKey | Null | received by | Publik / Sesuai Izin Modul |
| `confirmed_by_id` | ForeignKey | Null | confirmed by | Publik / Sesuai Izin Modul |
| `confirmed_at` | DateTimeField | Null | confirmed at | Publik / Sesuai Izin Modul |


### GoodsReceiptItem (`inventory_goodsreceiptitem`)
**Deskripsi:** GoodsReceiptItem(id, goods_receipt, product, qty_ordered, qty_actual, purchase_price, allocated_transport_cost, allocated_unloading_cost, effective_unit_cost, line_total, notes, created_at, updated_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `goods_receipt_id` | ForeignKey | Wajib (Required) | goods receipt | Publik / Sesuai Izin Modul |
| `product_id` | ForeignKey | Wajib (Required) | product | Publik / Sesuai Izin Modul |
| `qty_ordered` | DecimalField | Wajib (Required) | Disalin otomatis dari Purchase Order saat pembuatan BPB | Publik / Sesuai Izin Modul |
| `qty_actual` | DecimalField | Wajib (Required) | Fisik barang aktual yang diterima dan dihitung oleh staf gudang | Publik / Sesuai Izin Modul |
| `purchase_price` | DecimalField | Wajib (Required) | purchase price | Publik / Sesuai Izin Modul |
| `allocated_transport_cost` | DecimalField | Wajib (Required) | Alokasi proporsional ongkir masuk yang menambah nilai kapitalisasi HPP | Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang) |
| `allocated_unloading_cost` | DecimalField | Wajib (Required) | Memo alokasi biaya kuli bongkar (TIDAK BOLEH masuk ke kapitalisasi HPP) | Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang) |
| `effective_unit_cost` | DecimalField | Wajib (Required) | HPP efektif satuan masuk = (qty_actual * purchase_price + allocated_transport) / qty_actual | Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang) |
| `line_total` | DecimalField | Wajib (Required) | line total | Publik / Sesuai Izin Modul |
| `notes` | CharField | Blank | notes | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |


### Delivery (`inventory_delivery`)
**Deskripsi:** Delivery(id, created_at, updated_at, created_by, updated_by, delivery_number, sales_invoice, customer, customer_name_snapshot, delivery_date, driver_name, vehicle_number, status, confirmed_at, confirmed_by, notes)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `delivery_number` | CharField | Wajib (Required) | delivery number | Publik / Sesuai Izin Modul |
| `sales_invoice_id` | OneToOneField | Wajib (Required) | Alur Invoice-First: Surat Jalan terikat 1:1 pada Sales Invoice | Publik / Sesuai Izin Modul |
| `customer_id` | ForeignKey | Wajib (Required) | customer | Publik / Sesuai Izin Modul |
| `customer_name_snapshot` | CharField | Blank | customer name snapshot | Publik / Sesuai Izin Modul |
| `delivery_date` | DateField | Wajib (Required) | delivery date | Publik / Sesuai Izin Modul |
| `driver_name` | CharField | Blank | driver name | Publik / Sesuai Izin Modul |
| `vehicle_number` | CharField | Blank | vehicle number | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `confirmed_at` | DateTimeField | Null | confirmed at | Publik / Sesuai Izin Modul |
| `confirmed_by_id` | ForeignKey | Null | confirmed by | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |


### DeliveryItem (`inventory_deliveryitem`)
**Deskripsi:** DeliveryItem(id, delivery, product, sales_invoice_item, qty, qty_delivered, hpp_at_delivery, total_cogs, created_at, updated_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `delivery_id` | ForeignKey | Wajib (Required) | delivery | Publik / Sesuai Izin Modul |
| `product_id` | ForeignKey | Wajib (Required) | product | Publik / Sesuai Izin Modul |
| `sales_invoice_item_id` | ForeignKey | Null | sales invoice item | Publik / Sesuai Izin Modul |
| `qty` | DecimalField | Wajib (Required) | Kuantitas pesanan yang direncanakan dikirim | Publik / Sesuai Izin Modul |
| `qty_delivered` | DecimalField | Null | Null saat draf; diisi angka aktual saat konfirmasi oleh staf Gudang (bisa 0 jika batal terkirim) | Publik / Sesuai Izin Modul |
| `hpp_at_delivery` | DecimalField | Wajib (Required) | Snapshot Moving Average HPP saat status surat jalan menjadi confirmed | Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang) |
| `total_cogs` | DecimalField | Wajib (Required) | Total HPP yang dibukukan = qty_delivered * hpp_at_delivery | Direktur, Accounting, Finance (Hidden for Sales, Admin Ops, Gudang) |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |


### StockMovement (`inventory_stockmovement`)
**Deskripsi:** StockMovement(id, product, movement_date, movement_type, qty, unit_cost, total_cost, stock_before, stock_after, hpp_after, goods_receipt_item, delivery_item, reference_type, reference_id, notes, created_by, created_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `product_id` | ForeignKey | Wajib (Required) | product | Publik / Sesuai Izin Modul |
| `movement_date` | DateTimeField | Wajib (Required) | movement date | Publik / Sesuai Izin Modul |
| `movement_type` | CharField | Wajib (Required) | movement type | Publik / Sesuai Izin Modul |
| `qty` | DecimalField | Wajib (Required) | Kuantitas mutasi (selalu positif, arah ditentukan oleh movement_type) | Publik / Sesuai Izin Modul |
| `unit_cost` | DecimalField | Wajib (Required) | unit cost | Publik / Sesuai Izin Modul |
| `total_cost` | DecimalField | Wajib (Required) | total cost | Publik / Sesuai Izin Modul |
| `stock_before` | DecimalField | Wajib (Required) | stock before | Publik / Sesuai Izin Modul |
| `stock_after` | DecimalField | Wajib (Required) | stock after | Publik / Sesuai Izin Modul |
| `hpp_after` | DecimalField | Wajib (Required) | hpp after | Publik / Sesuai Izin Modul |
| `goods_receipt_item_id` | ForeignKey | Null | goods receipt item | Publik / Sesuai Izin Modul |
| `delivery_item_id` | ForeignKey | Null | delivery item | Publik / Sesuai Izin Modul |
| `reference_type` | CharField | Wajib (Required) | reference type | Publik / Sesuai Izin Modul |
| `reference_id` | CharField | Wajib (Required) | reference id | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | created by | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |


## Modul: FINANCE

### ChartOfAccounts (`finance_chartofaccounts`)
**Deskripsi:** ChartOfAccounts(id, created_at, updated_at, created_by, updated_by, account_code, name, account_type, parent, report_group, normal_balance, is_cash_bank, is_postable, is_active)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `account_code` | CharField | Wajib (Required) | account code | Publik / Sesuai Izin Modul |
| `name` | CharField | Wajib (Required) | name | Publik / Sesuai Izin Modul |
| `account_type` | CharField | Wajib (Required) | account type | Publik / Sesuai Izin Modul |
| `parent_id` | ForeignKey | Null | parent | Publik / Sesuai Izin Modul |
| `report_group` | CharField | Wajib (Required) | report group | Publik / Sesuai Izin Modul |
| `normal_balance` | CharField | Wajib (Required) | normal balance | Publik / Sesuai Izin Modul |
| `is_cash_bank` | BooleanField | Wajib (Required) | Centang jika akun ini adalah Kas Tunai atau Rekening Bank | Publik / Sesuai Izin Modul |
| `is_postable` | BooleanField | Wajib (Required) | Hanya akun postable (detail) yang dapat dipilih dalam baris jurnal | Publik / Sesuai Izin Modul |
| `is_active` | BooleanField | Wajib (Required) | is active | Publik / Sesuai Izin Modul |


### AccountingPeriod (`finance_accountingperiod`)
**Deskripsi:** AccountingPeriod(id, created_at, updated_at, created_by, updated_by, period_name, start_date, end_date, status, submitted_by, submitted_at, closed_by, closed_at, reopened_by, reopened_at, reopen_reason, closing_notes)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `period_name` | CharField | Wajib (Required) | Contoh: 2026-11 (November 2026) | Publik / Sesuai Izin Modul |
| `start_date` | DateField | Wajib (Required) | start date | Publik / Sesuai Izin Modul |
| `end_date` | DateField | Wajib (Required) | end date | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `submitted_by_id` | ForeignKey | Null | submitted by | Publik / Sesuai Izin Modul |
| `submitted_at` | DateTimeField | Null | submitted at | Publik / Sesuai Izin Modul |
| `closed_by_id` | ForeignKey | Null | closed by | Publik / Sesuai Izin Modul |
| `closed_at` | DateTimeField | Null | closed at | Publik / Sesuai Izin Modul |
| `reopened_by_id` | ForeignKey | Null | reopened by | Publik / Sesuai Izin Modul |
| `reopened_at` | DateTimeField | Null | reopened at | Publik / Sesuai Izin Modul |
| `reopen_reason` | TextField | Blank | reopen reason | Publik / Sesuai Izin Modul |
| `closing_notes` | TextField | Blank | closing notes | Publik / Sesuai Izin Modul |


### GeneralLedger (`finance_generalledger`)
**Deskripsi:** GeneralLedger(id, created_at, updated_at, transaction_number, period, date, reference_type, reference_id, description, is_posted, reversal_of, posted_by)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `transaction_number` | CharField | Wajib (Required) | transaction number | Publik / Sesuai Izin Modul |
| `period_id` | ForeignKey | Wajib (Required) | period | Publik / Sesuai Izin Modul |
| `date` | DateField | Wajib (Required) | date | Publik / Sesuai Izin Modul |
| `reference_type` | CharField | Wajib (Required) | reference type | Publik / Sesuai Izin Modul |
| `reference_id` | CharField | Wajib (Required) | reference id | Publik / Sesuai Izin Modul |
| `description` | TextField | Blank | description | Publik / Sesuai Izin Modul |
| `is_posted` | BooleanField | Wajib (Required) | is posted | Publik / Sesuai Izin Modul |
| `reversal_of_id` | ForeignKey | Null | reversal of | Publik / Sesuai Izin Modul |
| `posted_by_id` | ForeignKey | Wajib (Required) | posted by | Publik / Sesuai Izin Modul |


### GeneralLedgerLine (`finance_generalledgerline`)
**Deskripsi:** GeneralLedgerLine(id, ledger_entry, account, debit, credit, memo, created_at, updated_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `ledger_entry_id` | ForeignKey | Wajib (Required) | ledger entry | Publik / Sesuai Izin Modul |
| `account_id` | ForeignKey | Wajib (Required) | account | Publik / Sesuai Izin Modul |
| `debit` | DecimalField | Wajib (Required) | debit | Publik / Sesuai Izin Modul |
| `credit` | DecimalField | Wajib (Required) | credit | Publik / Sesuai Izin Modul |
| `memo` | CharField | Blank | memo | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |


### SalesInvoice (`finance_salesinvoice`)
**Deskripsi:** SalesInvoice(id, created_at, updated_at, created_by, updated_by, invoice_number, customer, customer_name_snapshot, invoice_date, due_date, payment_method, subtotal, discount_amount, total_amount, paid_amount, status, journal_entry, revision_no, notes)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `invoice_number` | CharField | Wajib (Required) | invoice number | Publik / Sesuai Izin Modul |
| `customer_id` | ForeignKey | Wajib (Required) | customer | Publik / Sesuai Izin Modul |
| `customer_name_snapshot` | CharField | Blank | customer name snapshot | Publik / Sesuai Izin Modul |
| `invoice_date` | DateField | Wajib (Required) | invoice date | Publik / Sesuai Izin Modul |
| `due_date` | DateField | Wajib (Required) | due date | Publik / Sesuai Izin Modul |
| `payment_method` | CharField | Wajib (Required) | payment method | Publik / Sesuai Izin Modul |
| `subtotal` | DecimalField | Wajib (Required) | subtotal | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `discount_amount` | DecimalField | Wajib (Required) | discount amount | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `total_amount` | DecimalField | Wajib (Required) | total amount | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `paid_amount` | DecimalField | Wajib (Required) | paid amount | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `journal_entry_id` | ForeignKey | Null | journal entry | Publik / Sesuai Izin Modul |
| `revision_no` | PositiveIntegerField | Wajib (Required) | Nomor revisi jika ada kekurangan fisik barang kirim | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |


### SalesInvoiceItem (`finance_salesinvoiceitem`)
**Deskripsi:** SalesInvoiceItem(id, invoice, product, qty_ordered, qty_delivered, unit_price, discount_amount, line_total, created_at, updated_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `invoice_id` | ForeignKey | Wajib (Required) | invoice | Publik / Sesuai Izin Modul |
| `product_id` | ForeignKey | Wajib (Required) | product | Publik / Sesuai Izin Modul |
| `qty_ordered` | DecimalField | Wajib (Required) | Kuantitas yang dipesan pelanggan pada draf invoice | Publik / Sesuai Izin Modul |
| `qty_delivered` | DecimalField | Null | Kuantitas fisik aktual yang dikonfirmasi terkirim oleh Gudang | Publik / Sesuai Izin Modul |
| `unit_price` | DecimalField | Wajib (Required) | unit price | Publik / Sesuai Izin Modul |
| `discount_amount` | DecimalField | Wajib (Required) | discount amount | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `line_total` | DecimalField | Wajib (Required) | line total | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |


### SalesInvoiceRevision (`finance_salesinvoicerevision`)
**Deskripsi:** SalesInvoiceRevision(id, invoice, revised_by, revision_number, old_total, new_total, reason, created_at)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `invoice_id` | ForeignKey | Wajib (Required) | invoice | Publik / Sesuai Izin Modul |
| `revised_by_id` | ForeignKey | Wajib (Required) | revised by | Publik / Sesuai Izin Modul |
| `revision_number` | PositiveIntegerField | Wajib (Required) | revision number | Publik / Sesuai Izin Modul |
| `old_total` | DecimalField | Wajib (Required) | old total | Publik / Sesuai Izin Modul |
| `new_total` | DecimalField | Wajib (Required) | new total | Publik / Sesuai Izin Modul |
| `reason` | TextField | Wajib (Required) | reason | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |


### DebitNote (`finance_debitnote`)
**Deskripsi:** DebitNote(id, created_at, updated_at, created_by, updated_by, debit_note_number, goods_receipt, supplier, supplier_name_snapshot, date, amount, reason, status, journal_entry, period, issued_by)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `debit_note_number` | CharField | Wajib (Required) | debit note number | Publik / Sesuai Izin Modul |
| `goods_receipt_id` | ForeignKey | Wajib (Required) | goods receipt | Publik / Sesuai Izin Modul |
| `supplier_id` | ForeignKey | Wajib (Required) | supplier | Publik / Sesuai Izin Modul |
| `supplier_name_snapshot` | CharField | Blank | supplier name snapshot | Publik / Sesuai Izin Modul |
| `date` | DateField | Wajib (Required) | date | Publik / Sesuai Izin Modul |
| `amount` | DecimalField | Wajib (Required) | Nominal potongan klaim kekurangan barang = shortage_qty * purchase_price | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `reason` | TextField | Wajib (Required) | Alasan klaim kekurangan / kerusakan fisik barang | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `journal_entry_id` | ForeignKey | Null | journal entry | Publik / Sesuai Izin Modul |
| `period_id` | ForeignKey | Wajib (Required) | period | Publik / Sesuai Izin Modul |
| `issued_by_id` | ForeignKey | Wajib (Required) | issued by | Publik / Sesuai Izin Modul |


### Payment (`finance_payment`)
**Deskripsi:** Payment(id, created_at, updated_at, created_by, updated_by, payment_number, payment_method, category, direction, cash_bank_account, sales_invoice, goods_receipt, debit_note, payroll_slip, amount, payment_date, reference_number, status, notes, journal_entry, reversal_journal_entry)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `payment_number` | CharField | Wajib (Required) | payment number | Publik / Sesuai Izin Modul |
| `payment_method` | CharField | Wajib (Required) | payment method | Publik / Sesuai Izin Modul |
| `category` | CharField | Wajib (Required) | category | Publik / Sesuai Izin Modul |
| `direction` | CharField | Wajib (Required) | direction | Publik / Sesuai Izin Modul |
| `cash_bank_account_id` | ForeignKey | Wajib (Required) | Rekening Kas atau Bank yang digunakan untuk mutasi kas | Publik / Sesuai Izin Modul |
| `sales_invoice_id` | ForeignKey | Null | sales invoice | Publik / Sesuai Izin Modul |
| `goods_receipt_id` | ForeignKey | Null | goods receipt | Publik / Sesuai Izin Modul |
| `debit_note_id` | ForeignKey | Null | debit note | Publik / Sesuai Izin Modul |
| `payroll_slip_id` | ForeignKey | Null | payroll slip | Publik / Sesuai Izin Modul |
| `amount` | DecimalField | Wajib (Required) | amount | Semua kecuali Gudang (Gudang tidak memiliki akses nilai moneter) |
| `payment_date` | DateField | Wajib (Required) | payment date | Publik / Sesuai Izin Modul |
| `reference_number` | CharField | Blank | reference number | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |
| `journal_entry_id` | ForeignKey | Null | journal entry | Publik / Sesuai Izin Modul |
| `reversal_journal_entry_id` | ForeignKey | Null | reversal journal entry | Publik / Sesuai Izin Modul |


## Modul: HR

### Employee (`hr_employee`)
**Deskripsi:** Employee(id, created_at, updated_at, created_by, updated_by, employee_id, user, full_name, email, phone, national_id, tax_id, department, position, employment_status, joined_date, termination_date, base_salary, standard_allowance, bank_name, bank_account_number, bank_account_holder, bpjs_tk_number, bpjs_kes_number, is_active)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `employee_id` | CharField | Wajib (Required) | Nomor Induk Karyawan (NIK Internal) | Publik / Sesuai Izin Modul |
| `user_id` | OneToOneField | Null | Akun login sistem yang terhubung dengan data karyawan ini | Publik / Sesuai Izin Modul |
| `full_name` | CharField | Wajib (Required) | full name | Publik / Sesuai Izin Modul |
| `email` | CharField | Blank | email | Publik / Sesuai Izin Modul |
| `phone` | CharField | Blank | phone | Publik / Sesuai Izin Modul |
| `national_id` | CharField | Blank | Nomor Induk Kependudukan (KTP) | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `tax_id` | CharField | Blank | NPWP Pribadi | Publik / Sesuai Izin Modul |
| `department` | CharField | Wajib (Required) | department | Publik / Sesuai Izin Modul |
| `position` | CharField | Wajib (Required) | position | Publik / Sesuai Izin Modul |
| `employment_status` | CharField | Wajib (Required) | employment status | Publik / Sesuai Izin Modul |
| `joined_date` | DateField | Wajib (Required) | joined date | Publik / Sesuai Izin Modul |
| `termination_date` | DateField | Null | termination date | Publik / Sesuai Izin Modul |
| `base_salary` | DecimalField | Wajib (Required) | Gaji pokok bulanan (IDR) | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `standard_allowance` | DecimalField | Wajib (Required) | Tunjangan tetap bulanan (IDR) | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `bank_name` | CharField | Blank | bank name | Publik / Sesuai Izin Modul |
| `bank_account_number` | CharField | Blank | bank account number | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `bank_account_holder` | CharField | Blank | bank account holder | Publik / Sesuai Izin Modul |
| `bpjs_tk_number` | CharField | Blank | Nomor BPJS Ketenagakerjaan | Publik / Sesuai Izin Modul |
| `bpjs_kes_number` | CharField | Blank | Nomor BPJS Kesehatan | Publik / Sesuai Izin Modul |
| `is_active` | BooleanField | Wajib (Required) | is active | Publik / Sesuai Izin Modul |


### PayrollSlip (`hr_payrollslip`)
**Deskripsi:** PayrollSlip(id, created_at, updated_at, created_by, updated_by, slip_number, employee, period_month, period_year, base_salary, allowances, deductions, net_salary, payment_date, status, accrual_journal_entry, payment, approved_by, approved_at, paid_by, notes)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `slip_number` | CharField | Wajib (Required) | slip number | Publik / Sesuai Izin Modul |
| `employee_id` | ForeignKey | Wajib (Required) | employee | Publik / Sesuai Izin Modul |
| `period_month` | PositiveSmallIntegerField | Wajib (Required) | period month | Publik / Sesuai Izin Modul |
| `period_year` | PositiveSmallIntegerField | Wajib (Required) | period year | Publik / Sesuai Izin Modul |
| `base_salary` | DecimalField | Wajib (Required) | base salary | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `allowances` | DecimalField | Wajib (Required) | allowances | Publik / Sesuai Izin Modul |
| `deductions` | DecimalField | Wajib (Required) | deductions | Publik / Sesuai Izin Modul |
| `net_salary` | DecimalField | Wajib (Required) | net salary | Publik / Sesuai Izin Modul |
| `payment_date` | DateField | Null | payment date | Publik / Sesuai Izin Modul |
| `status` | CharField | Wajib (Required) | status | Publik / Sesuai Izin Modul |
| `accrual_journal_entry_id` | ForeignKey | Null | Jurnal pengakuan beban gaji saat slip gaji di-approve: Dr Beban Gaji / Cr Hutang Gaji | Publik / Sesuai Izin Modul |
| `payment_id` | ForeignKey | Null | Transaksi pencairan kas/bank saat gaji ditransfer: Dr Hutang Gaji / Cr Kas/Bank | Publik / Sesuai Izin Modul |
| `approved_by_id` | ForeignKey | Null | approved by | Publik / Sesuai Izin Modul |
| `approved_at` | DateTimeField | Null | approved at | Publik / Sesuai Izin Modul |
| `paid_by_id` | ForeignKey | Null | paid by | Publik / Sesuai Izin Modul |
| `notes` | TextField | Blank | notes | Publik / Sesuai Izin Modul |


### EmployeeMutation (`hr_employeemutation`)
**Deskripsi:** EmployeeMutation(id, created_at, updated_at, created_by, updated_by, employee, mutation_date, effective_date, mutation_type, previous_department, new_department, previous_position, new_position, previous_salary, new_salary, reason, approved_by, is_applied)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `created_by_id` | ForeignKey | Null | User yang membuat dokumen transaksi ini | Publik / Sesuai Izin Modul |
| `updated_by_id` | ForeignKey | Null | User terakhir yang memperbarui dokumen ini | Publik / Sesuai Izin Modul |
| `employee_id` | ForeignKey | Wajib (Required) | employee | Publik / Sesuai Izin Modul |
| `mutation_date` | DateField | Wajib (Required) | mutation date | Publik / Sesuai Izin Modul |
| `effective_date` | DateField | Wajib (Required) | effective date | Publik / Sesuai Izin Modul |
| `mutation_type` | CharField | Wajib (Required) | mutation type | Publik / Sesuai Izin Modul |
| `previous_department` | CharField | Wajib (Required) | previous department | Publik / Sesuai Izin Modul |
| `new_department` | CharField | Wajib (Required) | new department | Publik / Sesuai Izin Modul |
| `previous_position` | CharField | Wajib (Required) | previous position | Publik / Sesuai Izin Modul |
| `new_position` | CharField | Wajib (Required) | new position | Publik / Sesuai Izin Modul |
| `previous_salary` | DecimalField | Wajib (Required) | previous salary | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `new_salary` | DecimalField | Wajib (Required) | new salary | Eksklusif Direktur (Masked / Redacted untuk Admin/Finance/Accounting) |
| `reason` | TextField | Wajib (Required) | reason | Publik / Sesuai Izin Modul |
| `approved_by_id` | ForeignKey | Null | approved by | Publik / Sesuai Izin Modul |
| `is_applied` | BooleanField | Wajib (Required) | is applied | Publik / Sesuai Izin Modul |


### LaborRecord (`hr_laborrecord`)
**Deskripsi:** LaborRecord(id, created_at, updated_at, employee, record_date, record_type, title, description, hours, hourly_rate, recorded_by)

| Nama Kolom | Tipe Data | Null/Blank | Penjelasan & Aturan | Role Visibility |
|---|---|---|---|---|
| `id` | BigAutoField | Blank | ID | Publik / Sesuai Izin Modul |
| `created_at` | DateTimeField | Blank | created at | Publik / Sesuai Izin Modul |
| `updated_at` | DateTimeField | Blank | updated at | Publik / Sesuai Izin Modul |
| `employee_id` | ForeignKey | Wajib (Required) | employee | Publik / Sesuai Izin Modul |
| `record_date` | DateField | Wajib (Required) | record date | Publik / Sesuai Izin Modul |
| `record_type` | CharField | Wajib (Required) | record type | Publik / Sesuai Izin Modul |
| `title` | CharField | Wajib (Required) | title | Publik / Sesuai Izin Modul |
| `description` | TextField | Wajib (Required) | description | Publik / Sesuai Izin Modul |
| `hours` | DecimalField | Wajib (Required) | Jumlah jam lembur / kerja lapangan | Publik / Sesuai Izin Modul |
| `hourly_rate` | DecimalField | Wajib (Required) | Tarif per jam upah lembur kuli / staf | Publik / Sesuai Izin Modul |
| `recorded_by_id` | ForeignKey | Wajib (Required) | recorded by | Publik / Sesuai Izin Modul |

