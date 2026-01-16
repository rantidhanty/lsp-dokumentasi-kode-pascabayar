from typing import Any, Dict, List, Optional

from app.db import execute, fetch_all


def list_customers(conn) -> List[Dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT id_pelanggan, username, nama_pelanggan, nomor_kwh, id_tarif
        FROM pelanggan
        ORDER BY nama_pelanggan
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
               pl.nama_pelanggan, pl.username, pl.nomor_kwh,
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
