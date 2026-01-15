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

Catatan

Proyek ini dibuat untuk kebutuhan uji kompetensi dan fokus pada
pendokumentasian kode program sesuai standar LSP.

---

# 3 Cara buat repo GitHub (step singkat)

1. Buka **GitHub  New Repository**
2. Isi:
   - **Repository name**:
      `lsp-pembayaran-listrik-pascabayar`
   - Description:
     `Uji Kompetensi LSP  Dokumentasi Kode Program (Python & MySQL)`
   - Public
   - **Jangan centang** README (karena sudah ada)

3. Create repository

---

# 4 Push project ke GitHub (dari folder proyek)
```bash
git init
git add .
git commit -m "Initial commit - LSP Pembayaran Listrik Pascabayar"
git branch -M main
git remote add origin https://github.com/USERNAME/lsp-pembayaran-listrik-pascabayar.git
git push -u origin main
```
