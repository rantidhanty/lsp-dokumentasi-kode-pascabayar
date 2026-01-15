import unittest

from app.db import DBConfig, get_connection
from app.billing import get_customer_bills


class TestBilling(unittest.TestCase):
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

    def test_lihat_tagihan(self):
        """Uji pengambilan tagihan pelanggan"""
        bills = get_customer_bills(self.conn, "pel_test")
        self.assertIsInstance(bills, list)
        self.assertGreaterEqual(len(bills), 1)
        self.assertIn("status", bills[0])


if __name__ == "__main__":
    unittest.main()
