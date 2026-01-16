"""
auth.py - Authentication module.

Berisi fungsi login untuk administrator dan pelanggan.
Password dicek menggunakan hash SHA2-256 sesuai implementasi di database.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from mysql.connector import MySQLConnection
from .db import fetch_all


def login_admin(
    conn: MySQLConnection, username: str, password_plain: str
) -> Optional[Dict[str, Any]]:
    """
    Login untuk user admin/petugas.

    Args:
        conn: Koneksi MySQL.
        username: Username admin.
        password_plain: Password input (plain), akan di-hash di query.

    Returns:
        Dict data admin jika valid, atau None jika gagal login.
    """
    rows = fetch_all(
        conn,
        """
        SELECT id_user, username, nama_admin, id_level
        FROM user
        WHERE username = %s AND password = SHA2(%s, 256)
        """,
        (username, password_plain),
    )
    return rows[0] if rows else None


def login_pelanggan(
    conn: MySQLConnection, username: str, password_plain: str
) -> Optional[Dict[str, Any]]:
    """
    Login untuk pelanggan.

    Args:
        conn: Koneksi MySQL.
        username: Username pelanggan.
        password_plain: Password input (plain), akan di-hash di query.

    Returns:
        Dict data pelanggan jika valid, atau None jika gagal login.
    """
    rows = fetch_all(
        conn,
        """
        SELECT id_pelanggan, username, nama_pelanggan, nomor_kwh, id_tarif
        FROM pelanggan
        WHERE username = %s
          AND (password = SHA2(%s, 256) OR password = %s)
        """,
        (username, password_plain, password_plain),
    )
    return rows[0] if rows else None
