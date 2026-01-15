"""
usage.py - Electricity usage CRUD module.

Berisi fungsi untuk menambah, mengubah, menghapus, dan membaca data penggunaan listrik.
"""

from __future__ import annotations
from typing import Any, Dict, List
from mysql.connector import MySQLConnection
from .db import execute, fetch_all


def create_usage(
    conn: MySQLConnection,
    id_pelanggan: int,
    bulan: int,
    tahun: int,
    meter_awal: int,
    meter_akhir: int,
) -> int:
    """
    Menambahkan data penggunaan listrik.

    Catatan:
        Jika database memiliki trigger, maka insert penggunaan dapat otomatis membuat tagihan.

    Args:
        conn: Koneksi MySQL.
        id_pelanggan: ID pelanggan.
        bulan: Bulan pemakaian (1-12).
        tahun: Tahun pemakaian.
        meter_awal: Angka meter awal.
        meter_akhir: Angka meter akhir.

    Returns:
        ID penggunaan yang baru dibuat.
    """
    return execute(
        conn,
        """
        INSERT INTO penggunaan (id_pelanggan, bulan, tahun, meter_awal, meter_akhir)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (id_pelanggan, bulan, tahun, meter_awal, meter_akhir),
    )


def list_usage_by_customer(
    conn: MySQLConnection, id_pelanggan: int
) -> List[Dict[str, Any]]:
    """
    Menampilkan daftar penggunaan pelanggan.

    Args:
        conn: Koneksi MySQL.
        id_pelanggan: ID pelanggan.

    Returns:
        List penggunaan.
    """
    return fetch_all(
        conn,
        """
        SELECT id_penggunaan, bulan, tahun, meter_awal, meter_akhir,
               (meter_akhir - meter_awal) AS kwh
        FROM penggunaan
        WHERE id_pelanggan = %s
        ORDER BY tahun, bulan
        """,
        (id_pelanggan,),
    )


def update_usage(
    conn: MySQLConnection, id_penggunaan: int, meter_awal: int, meter_akhir: int
) -> None:
    """
    Mengubah data meter pada penggunaan.

    Args:
        conn: Koneksi MySQL.
        id_penggunaan: ID penggunaan.
        meter_awal: Meter awal baru.
        meter_akhir: Meter akhir baru.
    """
    execute(
        conn,
        """
        UPDATE penggunaan
        SET meter_awal = %s, meter_akhir = %s
        WHERE id_penggunaan = %s
        """,
        (meter_awal, meter_akhir, id_penggunaan),
    )


def delete_usage(conn: MySQLConnection, id_penggunaan: int) -> None:
    """
    Menghapus data penggunaan.

    Perhatian:
        Jika tabel tagihan punya FK ke penggunaan tanpa CASCADE,
        maka data tagihan terkait harus dihapus dulu.

    Args:
        conn: Koneksi MySQL.
        id_penggunaan: ID penggunaan yang akan dihapus.
    """
    execute(conn, "DELETE FROM penggunaan WHERE id_penggunaan = %s", (id_penggunaan,))
