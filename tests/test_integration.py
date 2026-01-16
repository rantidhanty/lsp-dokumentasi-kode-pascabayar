import os
import time
import unittest

from dotenv import load_dotenv

from app.auth import login_pelanggan
from app.billing import get_customer_bills
from app.db import DBConfig, get_connection, execute, fetch_all
from app.usage import create_usage


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()

        cfg = DBConfig(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "app_admin"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "lsp_listrik"),
            port=int(os.getenv("DB_PORT", "3306")),
        )
        cls.conn = get_connection(cfg)

        # Ambil data pelanggan uji (pel_test)
        rows = fetch_all(
            cls.conn,
            "SELECT id_pelanggan, username FROM pelanggan WHERE username=%s",
            ("pel_test",),
        )
        if not rows:
            raise RuntimeError("Data uji pelanggan 'pel_test' tidak ditemukan.")
        cls.id_pelanggan = int(rows[0]["id_pelanggan"])

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_skenario1_login_ke_tagihan(self):
        """
        Skenario 1 (Integrasi auth -> billing):
        1) Login pelanggan
        2) Ambil tagihan berdasarkan username
        """
        user = login_pelanggan(self.conn, "pel_test", "pel123")
        self.assertIsNotNone(user, "Login seharusnya berhasil untuk data uji")

        bills = get_customer_bills(self.conn, "pel_test")
        self.assertIsInstance(bills, list)
        self.assertGreaterEqual(len(bills), 1, "Tagihan minimal harus ada 1 data")
        self.assertIn("status", bills[0])

    def test_skenario2_usage_trigger_ke_tagihan(self):
        """
        Skenario 2 (Integrasi usage -> trigger DB -> tagihan -> billing):
        1) Insert penggunaan (usage.create_usage)
        2) Trigger database otomatis membuat tagihan
        3) Tagihan bisa dibaca (billing.get_customer_bills)
        """

        # Buat bulan/tahun yang unik agar tidak bentrok
        # (pakai timestamp supaya selalu baru)
        bulan = 12
        tahun = 2099  # aman untuk data uji, kecil kemungkinan sudah ada

        meter_awal = 1000
        meter_akhir = 1100

        # Bersihkan data uji jika pernah ada (idempotent)
        # Hapus tagihan dulu (karena FK ke penggunaan)
        execute(
            self.conn,
            """
            DELETE t FROM tagihan t
            JOIN penggunaan p ON p.id_penggunaan = t.id_penggunaan
            WHERE p.id_pelanggan = %s AND p.bulan = %s AND p.tahun = %s
            """,
            (self.id_pelanggan, bulan, tahun),
        )
        # Hapus penggunaan
        execute(
            self.conn,
            "DELETE FROM penggunaan WHERE id_pelanggan=%s AND bulan=%s AND tahun=%s",
            (self.id_pelanggan, bulan, tahun),
        )

        # 1) Insert penggunaan via modul usage
        id_penggunaan = create_usage(
            self.conn,
            self.id_pelanggan,
            bulan,
            tahun,
            meter_awal,
            meter_akhir,
        )
        self.assertGreater(id_penggunaan, 0)

        # 2) Verifikasi trigger membuat tagihan
        # (beri jeda kecil kalau DB/trigger butuh waktu, biasanya instan)
        time.sleep(0.1)

        tagihan_rows = fetch_all(
            self.conn,
            """
            SELECT id_tagihan, id_penggunaan, id_pelanggan, bulan, tahun, jumlah_meter, status
            FROM tagihan
            WHERE id_penggunaan = %s
            """,
            (id_penggunaan,),
        )
        self.assertEqual(
            len(tagihan_rows), 1, "Tagihan harus terbentuk otomatis dari trigger"
        )
        self.assertEqual(int(tagihan_rows[0]["jumlah_meter"]), meter_akhir - meter_awal)

        # 3) Verifikasi bisa muncul di modul billing
        bills = get_customer_bills(self.conn, "pel_test")
        self.assertTrue(
            any(b.get("bulan") == bulan and b.get("tahun") == tahun for b in bills),
            "Tagihan hasil insert penggunaan harus tampil pada hasil billing",
        )


if __name__ == "__main__":
    unittest.main()
