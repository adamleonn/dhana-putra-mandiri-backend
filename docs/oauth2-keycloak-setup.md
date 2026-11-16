# Autentikasi & Otorisasi OAuth 2.0 / OpenID Connect (Keycloak)

Token demo `Bearer demo-*` **sudah dihapus**. Seluruh API hanya menerima access
token JWT yang diterbitkan Keycloak dan divalidasi backend.

## 1. Arsitektur

```
Browser ──(cookie HttpOnly)──▶ Next.js BFF :3000 ──(Bearer access token)──▶ Django API :8001
   │                               │  /api/auth/login     → redirect authorize (PKCE S256)
   │                               │  /api/auth/callback  → tukar code, verifikasi ID token
   └──── login form ──▶ Keycloak :8080 (realm dhana-putra)
```

| Komponen | Peran OAuth | Catatan |
|---|---|---|
| Keycloak realm `dhana-putra` | Authorization server / OIDC Provider | Discovery: `http://localhost:8080/realms/dhana-putra/.well-known/openid-configuration` |
| Client `dhana-putra-web` | Confidential client (Next.js BFF) | Authorization Code + PKCE S256, refresh token rotasi |
| Client `dhana-putra-api` | Resource server (Django) | Audience access token + pemilik client role `direktur/admin/gudang/stakeholder` |

**Frontend (BFF):** token tidak pernah masuk ke JavaScript/`localStorage`. Access,
refresh, dan ID token disimpan terenkripsi (AES-256-GCM) dalam cookie
`HttpOnly; SameSite=Lax; Path=/` (+ `Secure` dan prefiks `__Host-` saat HTTPS).
Browser memanggil `/api/backend/*` (same-origin); Route Handler menyisipkan
`Authorization: Bearer` ke Django dan otomatis me-refresh token (refresh paralel
di-dedupe agar aman terhadap rotasi refresh token).

**Backend:** `config/auth.py` + `config/oidc.py` memvalidasi signature (RS256 via
JWKS dari discovery, cache + refetch terbatas saat rotasi kunci), `iss`, `aud`,
`exp`/`nbf`/`iat`, `sub`, `azp` (allowlist), dan menolak ID token (`typ`).
Role dari klaim `resource_access.dhana-putra-api.roles` dipetakan ke empat peran
dan disinkronkan ke Django Group setiap request (IdP = sumber kebenaran).

**CSRF:** mutasi lewat BFF wajib `Origin` = `APP_BASE_URL` **dan** header
`x-dpm-csrf: 1`; cookie `SameSite=Lax`. API Django tidak memakai cookie
(SessionAuthentication dinonaktifkan untuk API), CORS tanpa kredensial.

## 2. Matriks akses endpoint (backend, deny-by-default)

| Endpoint | Baca | Tulis / aksi |
|---|---|---|
| `core/me` | D A G S | – |
| `core|finance/customers`, `suppliers` | D A G S | D A |
| `core/audit-logs` | D | – |
| `inventory/products` (+`stock-estimation`), `purchase-orders` | D A G S | D A |
| `inventory/goods-receipts` | D A G S | buat/ubah: D A · `confirm`: D G |
| `inventory/deliveries` | D A G S | buat/ubah: D A G · hapus: D A · `confirm`: D G |
| `inventory/stock-movements` | D A G S | – |
| `finance/chart-of-accounts`, `debit-notes` | D A S | D |
| `finance/accounting-periods` | D A S | D (`close/reopen/submit_period`: D) |
| `finance/general-ledger` | D S | – |
| `finance/sales-invoices` | D A S | D A · `revise`: D |
| `finance/payments` | D A S | D A |
| `finance/reports/*` (termasuk `sales-trends`) | D A S | – (Gudang **403**) |
| `hr/employees`, `hr/mutations` | D A S | D A |
| `hr/labor-records` | D A G S | D A G |
| `hr/payroll-slips` | D A S | `generate`, `approve`, CRUD: D |

D=Direktur, A=Admin, G=Gudang, S=Stakeholder. Pengguna tanpa peran → **403** di
semua endpoint. Flag `is_superuser` lokal **tidak** mem-bypass peran dari IdP.
Masking field (HPP untuk Admin, semua nominal untuk Gudang) tetap berlaku.

## 3. Setup Keycloak lokal

### 3.1 Menjalankan Keycloak (tanpa Docker, Java 21+)
```powershell
# unduh & ekstrak keycloak-26.x.zip dari github.com/keycloak/keycloak/releases
copy backend\keycloak\realm-dhana-putra.json keycloak-26.x\data\import\
$env:KC_BOOTSTRAP_ADMIN_USERNAME="kcadmin"
$env:KC_BOOTSTRAP_ADMIN_PASSWORD="<password-admin-lokal>"
# Windows: bila muncul "Unable to establish loopback connection", set tmpdir yang dapat ditulis:
$env:JAVA_OPTS_APPEND="-Djdk.net.unixdomain.tmpdir=C:/Windows/Temp"
keycloak-26.x\bin\kc.bat start-dev --http-port=8080 --import-realm
```
Dengan Docker: `docker run -p 8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=kcadmin -e KC_BOOTSTRAP_ADMIN_PASSWORD=... -v ./backend/keycloak:/opt/keycloak/data/import quay.io/keycloak/keycloak:26.8 start-dev --import-realm`

### 3.2 Isi realm (`backend/keycloak/realm-dhana-putra.json`)
- Realm `dhana-putra`: registrasi dimatikan, brute-force protection aktif,
  access token 5 menit, SSO idle 30 menit, **refresh token rotation**
  (`revokeRefreshToken=true`, `refreshTokenMaxReuse=0`).
- Client `dhana-putra-api`: semua flow login dimatikan; client role
  `direktur`, `admin`, `gudang`, `stakeholder`.
- Client `dhana-putra-web`: confidential, Standard Flow saja, PKCE `S256` wajib,
  `fullScopeAllowed=false` (hanya role API yang masuk token), audience mapper
  `dhana-putra-api`.
  - **Redirect URI:** `http://localhost:3000/api/auth/callback`
  - **Post logout redirect URI:** `http://localhost:3000/login*`
  - **Web origins:** `http://localhost:3000`
- User dev **tanpa password**: `direktur`, `admin`, `gudang`, `stakeholder`,
  `tanpa-peran` (untuk uji 403).

### 3.3 Password dev & client secret (tidak disimpan di source)
```bash
export KEYCLOAK_ADMIN=kcadmin KEYCLOAK_ADMIN_PASSWORD=<password-admin-lokal>
export KC_DEV_USER_PASSWORD=<password-dev-lokal>
cd backend
python keycloak/bootstrap_dev.py --set-passwords --write-client-secret ../frontend/.env.local
```
Atau manual: Admin Console → realm *dhana-putra* → Users → Credentials, dan
Clients → `dhana-putra-web` → Credentials → salin *Client secret* ke `OIDC_CLIENT_SECRET`.

## 4. Environment variable

Lihat `backend/.env.example` dan `frontend/.env.example`. Minimum lokal:

| Backend (`backend/.env`) | Nilai lokal |
|---|---|
| `OIDC_ISSUER` | `http://localhost:8080/realms/dhana-putra` |
| `OIDC_API_AUDIENCE` | `dhana-putra-api` |
| `OIDC_ALLOWED_CLIENT_IDS` | `dhana-putra-web` |
| `OIDC_ROLE_CLAIM_PATHS` | `resource_access.dhana-putra-api.roles` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:8001` |

| Frontend (`frontend/.env.local`) | Nilai lokal |
|---|---|
| `APP_BASE_URL` | `http://localhost:3000` |
| `API_BASE_URL` | `http://127.0.0.1:8001/api` |
| `OIDC_ISSUER` | `http://localhost:8080/realms/dhana-putra` |
| `OIDC_CLIENT_ID` | `dhana-putra-web` |
| `OIDC_CLIENT_SECRET` | dari Keycloak (jangan di-commit) |
| `SESSION_SECRET` | ≥32 karakter acak |

**Production:** `APP_ENV=production` memaksa `OIDC_ISSUER` HTTPS,
`OIDC_ALLOWED_CLIENT_IDS` terisi, cookie `Secure`, dan origin CORS/CSRF HTTPS.
Next.js (`NODE_ENV=production`) menolak start tanpa HTTPS pada `APP_BASE_URL`,
`OIDC_ISSUER`, dan cookie Secure. Daftarkan redirect URI production yang persis
(`https://<domain>/api/auth/callback`) dan ganti `localhost` di realm.

## 5. Migrasi pengguna lama

Data transaksi, produk, laporan, dan role **tidak berubah**. Pengguna lama
dipertahankan (primary key sama, sehingga relasi `created_by` dsb. tetap utuh):

1. Ekspor pengguna aktif + peran ke format Partial Import Keycloak (tanpa password):
   ```bash
   python manage.py export_keycloak_users --output keycloak/users-import.json
   ```
   Import di Admin Console → Realm settings → *Partial import*. User mendapat
   required action `UPDATE_PASSWORD`.
2. Login OIDC pertama dengan `preferred_username` sama akan **menautkan** user
   lokal (`oidc_issuer` + `oidc_subject`) bila `OIDC_LINK_EXISTING_BY_USERNAME=True`.
   Username yang sudah tertaut ke subject lain ditolak (anti-takeover).
3. Setelah semua tertaut, set `OIDC_LINK_EXISTING_BY_USERNAME=False`.
4. Peran retired (Sales/Finance/Accounting) tidak dipetakan → akses 403.

## 6. Menjalankan aplikasi

```bash
# 1. PostgreSQL & Keycloak berjalan (lihat §3)
# 2. Backend
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
# 3. Frontend
cd frontend
npm run dev            # http://localhost:3000 → "Masuk dengan SSO"
```

## 7. Pengujian

```bash
cd backend && python manage.py test            # termasuk core/test_oidc_auth.py
cd frontend && npx tsc --noEmit && npm run lint
```
`core/test_oidc_auth.py` memakai kunci RSA & JWKS palsu (tanpa Keycloak):
token valid, kedaluwarsa, `nbf` di masa depan, issuer/audience/azp salah,
signature kunci lain, kid tak dikenal (refetch dibatasi), HS256 *algorithm
confusion*, `alg=none`, ID token sebagai access token, token demo lama, user
tanpa peran, penautan/anti-takeover user, sinkronisasi & pencabutan peran, dan
matriks seluruh endpoint × empat peran.
