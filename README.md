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
