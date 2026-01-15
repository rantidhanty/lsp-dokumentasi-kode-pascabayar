"""
main.py - Simple demo runner.

File ini digunakan untuk mendemokan pemanggilan fungsi login dan lihat tagihan.
Tidak fokus pada UI; fokus pada akses data.
"""

from __future__ import annotations
from app.db import DBConfig, get_connection
from app.auth import login_pelanggan
from app.billing import get_customer_bills


def main() -> None:
    cfg = DBConfig(
        host="localhost",
        user="app_admin",
        password="Admin#12345",
        database="lsp_listrik",
        port=3306,
    )

    conn = get_connection(cfg)

    # Demo login pelanggan
    user = login_pelanggan(conn, "pel_test", "pel123")
    if not user:
        print("Login gagal")
        return

    print("Login sukses:", user["nama_pelanggan"])

    # Demo lihat tagihan pelanggan
    bills = get_customer_bills(conn, "pel_test")
    print("Tagihan:", bills)


if __name__ == "__main__":
    main()
