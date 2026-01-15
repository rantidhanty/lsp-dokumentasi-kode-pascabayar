"""
db.py - Database connection and query helpers.

Module ini menyediakan fungsi koneksi dan eksekusi query ke MySQL
untuk aplikasi pembayaran listrik pascabayar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector import MySQLConnection


# =====================
# DATA CLASS KONFIGURASI
# =====================
@dataclass
class DBConfig:
    """Konfigurasi koneksi database MySQL."""

    host: str = "localhost"
    user: str = "root"
    password: str = ""
    database: str = "lsp_listrik"
    port: int = 3306


# =====================
# CUSTOM EXCEPTION
# =====================
class DatabaseError(Exception):
    """Error umum untuk masalah database (koneksi/query)."""


# =====================
# FUNGSI KONEKSI
# =====================
def get_connection(cfg: DBConfig) -> MySQLConnection:
    """
    Membuat koneksi ke MySQL.

    Args:
        cfg: Konfigurasi koneksi.

    Returns:
        Objek koneksi MySQL.

    Raises:
        DatabaseError: Jika koneksi gagal.
    """
    try:
        return mysql.connector.connect(
            host=cfg.host,
            user=cfg.user,
            password=cfg.password,
            database=cfg.database,
            port=cfg.port,
        )
    except Exception as exc:
        raise DatabaseError(f"Gagal koneksi database: {exc}") from exc


# =====================
# QUERY SELECT
# =====================
def fetch_all(
    conn: MySQLConnection, query: str, params: Optional[Tuple[Any, ...]] = None
) -> List[Dict[str, Any]]:
    """
    Menjalankan SELECT dan mengembalikan semua baris dalam bentuk list of dict.

    Args:
        conn: Koneksi MySQL aktif.
        query: SQL query SELECT.
        params: Parameter query (opsional).

    Returns:
        List data hasil query.

    Raises:
        DatabaseError: Jika query gagal.
    """
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        return cur.fetchall()
    except Exception as exc:
        raise DatabaseError(f"Query gagal: {exc}") from exc
    finally:
        cur.close()


# =====================
# QUERY NON-SELECT
# =====================
def execute(
    conn: MySQLConnection, query: str, params: Optional[Tuple[Any, ...]] = None
) -> int:
    """
    Menjalankan query INSERT/UPDATE/DELETE.

    Args:
        conn: Koneksi MySQL aktif.
        query: SQL non-select.
        params: Parameter query (opsional).

    Returns:
        lastrowid untuk INSERT, atau 0 untuk selain INSERT.

    Raises:
        DatabaseError: Jika eksekusi gagal.
    """
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        conn.commit()
        return int(cur.lastrowid or 0)
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(f"Eksekusi gagal: {exc}") from exc
    finally:
        cur.close()
