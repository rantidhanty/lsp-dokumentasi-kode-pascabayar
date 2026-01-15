import cProfile
import pstats
from pstats import SortKey

from app.db import DBConfig, get_connection
from app.auth import login_pelanggan
from app.billing import get_customer_bills


def run_once(conn):
    user = login_pelanggan(conn, "pel_test", "pel123")
    if user:
        _ = get_customer_bills(conn, "pel_test")


if __name__ == "__main__":
    cfg = DBConfig(
        host="localhost",
        user="app_admin",  # atau root
        password="Admin#12345",  # sesuaikan
        database="lsp_listrik",
        port=3306,
    )

    # Koneksi dibuat SEKALI saja
    conn = get_connection(cfg)

    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(200):  # diperbanyak biar kebaca
        run_once(conn)

    profiler.disable()

    stats = pstats.Stats(profiler).strip_dirs()
    stats.sort_stats(SortKey.CUMULATIVE).print_stats(25)
