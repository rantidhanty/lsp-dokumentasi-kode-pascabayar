"""
billing.py - Billing module.

Berisi fungsi untuk melihat tagihan pelanggan berdasarkan username.
"""

from __future__ import annotations
from typing import Any, Dict, List
from mysql.connector import MySQLConnection
from .db import fetch_all


def get_customer_bills(conn: MySQLConnection, username: str) -> List[Dict[str, Any]]:
    """
    Mengambil daftar tagihan pelanggan.

    Args:
        conn: Koneksi MySQL.
        username: Username pelanggan.

    Returns:
        List tagihan pelanggan (bisa kosong jika belum ada tagihan).
    """
    return fetch_all(
        conn,
        """
        SELECT
          t.id_tagihan, pl.nama_pelanggan, t.bulan, t.tahun, t.jumlah_meter, t.status
        FROM tagihan t
        JOIN pelanggan pl ON pl.id_pelanggan = t.id_pelanggan
        WHERE pl.username = %s
        ORDER BY t.tahun, t.bulan
        """,
        (username,),
    )
