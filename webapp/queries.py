from typing import Any, Dict, List, Optional

from app.db import execute, fetch_all


def list_customers(conn) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT pl.id_pelanggan,
               pl.username,
               pl.nama_pelanggan,
               pl.nomor_kwh,
               pl.alamat,
               pl.id_tarif,
               tr.daya,
               tr.tarifperkwh
        FROM pelanggan pl
        JOIN tarif tr ON tr.id_tarif = pl.id_tarif
        ORDER BY pl.nama_pelanggan
        """,
    )


def list_tariffs(conn) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT id_tarif, daya, tarifperkwh
        FROM tarif
        ORDER BY daya
        """,
    )


def list_admins(conn) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT id_user, username, nama_admin, id_level
        FROM user
        ORDER BY nama_admin
        """,
    )


def list_recent_payments(conn, limit: int = 5) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT p.id_pembayaran,
               p.id_tagihan,
               p.id_pelanggan,
               p.tanggal_pembayaran,
               p.total_bayar,
               pl.nama_pelanggan
        FROM pembayaran p
        JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
        ORDER BY p.tanggal_pembayaran DESC, p.id_pembayaran DESC
        LIMIT %s
        """,
        (limit,),
    )


def get_default_admin_id(conn) -> Optional[int]:
    rows = fetch_all(
        conn,
        "SELECT id_user FROM user ORDER BY id_user LIMIT 1",
    )
    return int(rows[0]["id_user"]) if rows else None


def has_payment_for_bill(conn, id_tagihan: int) -> bool:
    rows = fetch_all(
        conn,
        "SELECT id_pembayaran FROM pembayaran WHERE id_tagihan = %s LIMIT 1",
        (id_tagihan,),
    )
    return bool(rows)


def create_payment(
    conn,
    id_tagihan: int,
    id_pelanggan: int,
    tanggal_pembayaran: str,
    bulan_bayar: int,
    biaya_admin: float,
    total_bayar: float,
    id_user: int,
) -> int:
    return execute(
        conn,
        """
        INSERT INTO pembayaran (id_tagihan, id_pelanggan, tanggal_pembayaran, bulan_bayar, biaya_admin, total_bayar, id_user)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (id_tagihan, id_pelanggan, tanggal_pembayaran, bulan_bayar, biaya_admin, total_bayar, id_user),
    )


def list_monthly_reports(conn) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT t.tahun,
               t.bulan,
               COUNT(*) AS total_tagihan,
               SUM(CASE WHEN t.status = 'SUDAH BAYAR' THEN 1 ELSE 0 END) AS tagihan_lunas,
               SUM(CASE WHEN t.status <> 'SUDAH BAYAR' THEN 1 ELSE 0 END) AS tagihan_belum,
               COUNT(DISTINCT t.id_pelanggan) AS total_pelanggan,
               ROUND(SUM(t.jumlah_meter * tr.tarifperkwh), 0) AS total_bayar
        FROM tagihan t
        JOIN pelanggan pl ON pl.id_pelanggan = t.id_pelanggan
        JOIN tarif tr ON tr.id_tarif = pl.id_tarif
        GROUP BY t.tahun, t.bulan
        ORDER BY t.tahun DESC, t.bulan DESC
        """,
    )


def get_monthly_report(conn, tahun: int, bulan: int) -> Optional[Dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT t.tahun,
               t.bulan,
               COUNT(*) AS total_tagihan,
               SUM(CASE WHEN t.status = 'SUDAH BAYAR' THEN 1 ELSE 0 END) AS tagihan_lunas,
               SUM(CASE WHEN t.status <> 'SUDAH BAYAR' THEN 1 ELSE 0 END) AS tagihan_belum,
               COUNT(DISTINCT t.id_pelanggan) AS total_pelanggan,
               ROUND(SUM(t.jumlah_meter * tr.tarifperkwh), 0) AS total_bayar
        FROM tagihan t
        JOIN pelanggan pl ON pl.id_pelanggan = t.id_pelanggan
        JOIN tarif tr ON tr.id_tarif = pl.id_tarif
        WHERE t.tahun = %s AND t.bulan = %s
        GROUP BY t.tahun, t.bulan
        """,
        (tahun, bulan),
    )
    return rows[0] if rows else None


def list_monthly_report_details(conn, tahun: int, bulan: int) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT pl.nama_pelanggan,
               pl.nomor_kwh,
               pl.alamat,
               p.meter_awal,
               p.meter_akhir,
               t.jumlah_meter,
               tr.tarifperkwh,
               t.status,
               ROUND(t.jumlah_meter * tr.tarifperkwh, 0) AS total_bayar
        FROM tagihan t
        JOIN pelanggan pl ON pl.id_pelanggan = t.id_pelanggan
        JOIN tarif tr ON tr.id_tarif = pl.id_tarif
        LEFT JOIN penggunaan p
          ON p.id_pelanggan = t.id_pelanggan
         AND p.bulan = t.bulan
         AND p.tahun = t.tahun
        WHERE t.tahun = %s AND t.bulan = %s
        ORDER BY pl.nama_pelanggan
        """,
        (tahun, bulan),
    )


def get_usage_by_customer_period(
    conn, id_pelanggan: int, bulan: int, tahun: int
) -> Optional[Dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT meter_awal, meter_akhir
        FROM penggunaan
        WHERE id_pelanggan = %s AND bulan = %s AND tahun = %s
        """,
        (id_pelanggan, bulan, tahun),
    )
    return rows[0] if rows else None




def create_customer(
    conn,
    username: str,
    password_plain: str,
    nama_pelanggan: str,
    nomor_kwh: str,
    alamat: str,
    id_tarif: int,
) -> int:
    return execute(
        conn,
        """
        INSERT INTO pelanggan (username, password, nomor_kwh, nama_pelanggan, alamat, id_tarif)
        VALUES (%s, SHA2(%s, 256), %s, %s, %s, %s)
        """,
        (username, password_plain, nomor_kwh, nama_pelanggan, alamat, id_tarif),
    )


def create_admin(
    conn,
    username: str,
    password_plain: str,
    nama_admin: str,
    id_level: int,
) -> int:
    return execute(
        conn,
        """
        INSERT INTO user (username, password, nama_admin, id_level)
        VALUES (%s, SHA2(%s, 256), %s, %s)
        """,
        (username, password_plain, nama_admin, id_level),
    )


def update_admin(
    conn,
    id_user: int,
    username: str,
    nama_admin: str,
    id_level: int,
    password_plain: Optional[str] = None,
) -> None:
    if password_plain:
        execute(
            conn,
            """
            UPDATE user
            SET username = %s,
                password = SHA2(%s, 256),
                nama_admin = %s,
                id_level = %s
            WHERE id_user = %s
            """,
            (username, password_plain, nama_admin, id_level, id_user),
        )
        return

    execute(
        conn,
        """
        UPDATE user
        SET username = %s,
            nama_admin = %s,
            id_level = %s
        WHERE id_user = %s
        """,
        (username, nama_admin, id_level, id_user),
    )


def delete_admin(conn, id_user: int) -> None:
    execute(
        conn,
        "DELETE FROM user WHERE id_user = %s",
        (id_user,),
    )


def list_usages(conn) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT p.id_penggunaan, p.id_pelanggan, p.bulan, p.tahun,
               p.meter_awal, p.meter_akhir,
               (p.meter_akhir - p.meter_awal) AS kwh,
               pl.nama_pelanggan, pl.username
        FROM penggunaan p
        JOIN pelanggan pl ON pl.id_pelanggan = p.id_pelanggan
        ORDER BY p.tahun DESC, p.bulan DESC
        """,
    )


def get_usage(conn, id_penggunaan: int) -> Optional[Dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT id_penggunaan, id_pelanggan, bulan, tahun, meter_awal, meter_akhir
        FROM penggunaan
        WHERE id_penggunaan = %s
        """,
        (id_penggunaan,),
    )
    return rows[0] if rows else None


def get_last_usage_for_customer(conn, id_pelanggan: int) -> Optional[Dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT bulan, tahun, meter_akhir
        FROM penggunaan
        WHERE id_pelanggan = %s
        ORDER BY tahun DESC, bulan DESC
        LIMIT 1
        """,
        (id_pelanggan,),
    )
    return rows[0] if rows else None


def get_customer(conn, id_pelanggan: int) -> Optional[Dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT id_pelanggan, username, nama_pelanggan, nomor_kwh, alamat, id_tarif
        FROM pelanggan
        WHERE id_pelanggan = %s
        """,
        (id_pelanggan,),
    )
    return rows[0] if rows else None


def list_bills(
    conn, id_pelanggan: Optional[int] = None, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    where_clauses = []
    params = []

    if id_pelanggan is not None:
        where_clauses.append("t.id_pelanggan = %s")
        params.append(id_pelanggan)

    if status is not None:
        where_clauses.append("t.status = %s")
        params.append(status)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    return fetch_all(
        conn,
        f"""
        SELECT t.id_tagihan, t.id_pelanggan, t.bulan, t.tahun,
               t.jumlah_meter, t.status,
               pl.nama_pelanggan, pl.username, pl.nomor_kwh,
               tr.tarifperkwh,
               ROUND(t.jumlah_meter * tr.tarifperkwh, 0) AS total_bayar
        FROM tagihan t
        JOIN pelanggan pl ON pl.id_pelanggan = t.id_pelanggan
        JOIN tarif tr ON tr.id_tarif = pl.id_tarif
        {where_sql}
        ORDER BY t.tahun DESC, t.bulan DESC
        """,
        tuple(params) if params else None,
    )


def get_bill(conn, id_tagihan: int) -> Optional[Dict[str, Any]]:
    rows = fetch_all(
        conn,
        """
        SELECT t.id_tagihan, t.id_pelanggan, t.bulan, t.tahun,
               t.jumlah_meter, t.status,
               pl.nama_pelanggan, pl.username, pl.nomor_kwh, pl.alamat,
               tr.tarifperkwh,
               ROUND(t.jumlah_meter * tr.tarifperkwh, 0) AS total_bayar
        FROM tagihan t
        JOIN pelanggan pl ON pl.id_pelanggan = t.id_pelanggan
        JOIN tarif tr ON tr.id_tarif = pl.id_tarif
        WHERE t.id_tagihan = %s
        """,
        (id_tagihan,),
    )
    return rows[0] if rows else None


def update_bill_status(conn, id_tagihan: int, status: str) -> None:
    execute(
        conn,
        "UPDATE tagihan SET status = %s WHERE id_tagihan = %s",
        (status, id_tagihan),
    )


def get_admin_stats(conn) -> Dict[str, int]:
    total_pelanggan = fetch_all(conn, "SELECT COUNT(*) AS total FROM pelanggan")[0][
        "total"
    ]
    total_penggunaan = fetch_all(conn, "SELECT COUNT(*) AS total FROM penggunaan")[0][
        "total"
    ]
    tagihan_belum = fetch_all(
        conn, "SELECT COUNT(*) AS total FROM tagihan WHERE status <> 'SUDAH BAYAR'"
    )[0]["total"]
    tagihan_lunas = fetch_all(
        conn, "SELECT COUNT(*) AS total FROM tagihan WHERE status = 'SUDAH BAYAR'"
    )[0]["total"]

    return {
        "total_pelanggan": int(total_pelanggan),
        "total_penggunaan": int(total_penggunaan),
        "tagihan_belum": int(tagihan_belum),
        "tagihan_lunas": int(tagihan_lunas),
    }
