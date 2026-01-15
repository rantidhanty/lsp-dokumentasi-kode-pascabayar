import unittest

from app.db import DBConfig, get_connection
from app.auth import login_pelanggan


class TestLoginPelanggan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = DBConfig(
            host="localhost",
            user="app_admin",
            password="Admin#12345",
            database="lsp_listrik",
            port=3306,
        )
        cls.conn = get_connection(cfg)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_login_berhasil(self):
        """Uji login dengan username dan password valid"""
        user = login_pelanggan(self.conn, "pel_test", "pel123")
        self.assertIsNotNone(user)
        self.assertEqual(user["nama_pelanggan"], "Test Pelanggan")

    def test_login_gagal(self):
        """Uji login dengan password salah"""
        user = login_pelanggan(self.conn, "pel_test", "salah")
        self.assertIsNone(user)


if __name__ == "__main__":
    unittest.main()
