"""
main.py - Simple demo runner.

File ini digunakan untuk mendemokan pemanggilan fungsi login dan lihat tagihan.
Tidak fokus pada UI; fokus pada akses data.
"""

# =====================
# IMPORT
# =====================
import os
from dotenv import load_dotenv

# from __future__ import annotations  # (dikomen, tidak dihapus)

from app.db import DBConfig, get_connection
from app.auth import login_pelanggan
from app.billing import get_customer_bills


def main() -> None:
    # Load konfigurasi dari file .env
    load_dotenv()

    # =====================
    # KONFIGURASI DATABASE (SEBELUM – HARDCODE)
    # =====================
    # cfg = DBConfig(
    #     host="localhost",
    #     user="app_admin",
    #     password="Admin#12345",
    #     database="lsp_listrik",
    #     port=3306,
    # )

    # =====================
    # KONFIGURASI DATABASE (SESUDAH – .env)
    # =====================
    cfg = DBConfig(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "lsp_listrik"),
        port=int(os.getenv("DB_PORT", "3306")),
    )

    # =====================
    # KONEKSI DATABASE
    # =====================
    conn = get_connection(cfg)

    try:
        # =====================
        # DEMO LOGIN PELANGGAN
        # =====================
        user = login_pelanggan(conn, "pel_test", "pel123")
        if not user:
            print("Login gagal")
            return

        print("Login sukses:", user["nama_pelanggan"])

        # =====================
        # DEMO LIHAT TAGIHAN
        # =====================
        bills = get_customer_bills(conn, "pel_test")
        print("Tagihan:", bills)

    finally:
        # =====================
        # TUTUP KONEKSI DATABASE
        # =====================
        conn.close()


if __name__ == "__main__":
    main()
