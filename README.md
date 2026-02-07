# LSP Pembayaran Listrik Pascabayar
Dokumentasi Kode Program

## Deskripsi
Proyek ini dibuat untuk memenuhi Uji Kompetensi LSP pada unit
**J.620100.023.02  Membuat Dokumen Kode Program**.

Fokus proyek adalah dokumentasi kode backend aplikasi pembayaran listrik
pascabayar menggunakan Python dan MySQL, serta generate dokumentasi otomatis
dalam bentuk HTML.

---

## Fitur
- Login pelanggan dan administrator
- CRUD data penggunaan listrik
- Menampilkan tagihan pelanggan
- Dokumentasi otomatis kode program (HTML)

---

## Teknologi yang Digunakan
- **Python 3.x**
- **MySQL** (database: `lsp_listrik`)
- **Library Python**:
  - `mysql-connector-python`  koneksi basis data MySQL
  - `pdoc`  generate dokumentasi kode program

---

## Struktur Folder Proyek
```
lsp-pembayaran-listrik-pascabayar/
  app/
    __init__.py
    db.py # Koneksi database & helper query
    auth.py # Modul login
    usage.py # CRUD penggunaan listrik
    billing.py # Lihat tagihan pelanggan
    main.py # Demo pemanggilan fungsi
  docs/ # Hasil generate dokumentasi HTML (pdoc)
  requirements.txt
  README.md
```

---

## Setup Singkat
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Generate Dokumentasi
```bash
pdoc -o docs app
```

Cara membuka dokumentasi (HTML)
- Windows (PowerShell):
  ```powershell
  start "" ".\docs\index.html"
  ```
- Atau langsung buka file `docs/index.html` lewat File Explorer.

Catatan

Proyek ini dibuat untuk kebutuhan uji kompetensi dan fokus pada
pendokumentasian kode program sesuai standar LSP.

---

## Web App (Flask)
Menjalankan aplikasi web dengan fitur login, CRUD, tagihan, dan pembayaran (dummy/Midtrans).

### Menjalankan
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Akses aplikasi:
- http://127.0.0.1:5000

### Konfigurasi .env (contoh)
```
SECRET_KEY=dev-secret
DB_HOST=localhost
DB_USER=app_admin
DB_PASSWORD=Admin#12345
DB_NAME=lsp_listrik
DB_PORT=3306

MIDTRANS_SERVER_KEY=SB-Mid-server-xxxx
MIDTRANS_CLIENT_KEY=SB-Mid-client-xxxx
MIDTRANS_IS_PRODUCTION=false
```

Jika key Midtrans belum diisi, aplikasi otomatis berjalan pada mode dummy (simulasi pembayaran).


---

## Analisis Proyek (10 Aspek)
Bagian ini disiapkan untuk kebutuhan presentasi.

1. Skalabilitas
- Arsitektur saat ini: monolith Flask + MySQL single instance.
- Bottleneck potensial: query agregasi laporan bulanan dan list bills tanpa pagination penuh.
- Saran scaling: indexing DB (kolom filter utama), caching ringan dashboard, WSGI server (gunicorn/uwsgi), dan pemisahan service jika modul membesar.

2. Basis Data
- Entitas utama (terlihat dari query): pelanggan, user, penggunaan, tagihan, pembayaran, tarif.
- Ada asumsi trigger DB yang membuat tagihan otomatis saat insert penggunaan (lihat tests/test_integration.py).

3. Akses Basis Data
- Koneksi dan helper query terpusat di app/db.py (get_connection, fetch_all, execute).
- Query web app terstruktur di webapp/queries.py.
- Per request DB connection di webapp/db.py (g + teardown).

4. Algoritma
- Perhitungan kWh sederhana (meter_akhir - meter_awal) di query penggunaan.
- Rekap laporan bulanan memakai agregasi SQL (COUNT, SUM, GROUP BY).
- Proses pembayaran: update status tagihan + insert pembayaran (simulasi atau Midtrans).

5. Dokumentasi
- Docstring tersedia pada modul app/.
- Dokumentasi otomatis dengan pdoc (output HTML di docs/).

6. Debugging
- Flask debug mode aktif di run.py.
- Error logging untuk pembuatan PDF ada di webapp/routes.py.
- Validasi input dasar di form (contoh: meter_akhir >= meter_awal).

7. Profiling
- Profiling tersedia di profile_run.py (cProfile).
- Versi optimized ada di profile_run_optimized.py (koneksi DB dibuat sekali).

8. Code Review
- Struktur modul jelas (auth, usage, billing, queries).
- Area peningkatan: validasi input lebih ketat, pagination untuk list besar, dan error handling lebih spesifik.

9. Unit Testing
- Unit test dan integrasi tersedia di tests/.
- Test membutuhkan data DB contoh (pel_test) dan trigger tagihan aktif.

10. Integritas
- Integritas data bergantung pada constraint/trigger di DB.
- Transaksi dijaga dengan commit/rollback di app/db.py.
- Perlu FK/unique index untuk memperkuat konsistensi data.

---

## Cara Menjalankan (Ringkas)
1) Setup virtual env dan dependencies:
```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Siapkan .env (contoh):
```
SECRET_KEY=dev-secret
DB_HOST=localhost
DB_USER=app_admin
DB_PASSWORD=Admin#12345
DB_NAME=lsp_listrik
DB_PORT=3306

MIDTRANS_SERVER_KEY=SB-Mid-server-xxxx
MIDTRANS_CLIENT_KEY=SB-Mid-client-xxxx
MIDTRANS_IS_PRODUCTION=false
```

3) Jalankan web app:
```bash
python run.py
```
Akses: http://127.0.0.1:5000

4) Jalankan demo CLI (opsional):
```bash
python app/main.py
```

5) Jalankan test:
```bash
python -m unittest discover -s tests
```

6) Generate dokumentasi:
```bash
pdoc -o docs app
```

7) Profiling:
```bash
python profile_run.py
python profile_run_optimized.py
```
