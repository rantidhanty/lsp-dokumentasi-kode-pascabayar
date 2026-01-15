import cProfile
import pstats
from pstats import SortKey

from app.main import main

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    # Jalankan beberapa kali supaya profiling kebaca
    for _ in range(20):
        main()

    profiler.disable()

    stats = pstats.Stats(profiler).strip_dirs()
    stats.sort_stats(SortKey.CUMULATIVE).print_stats(25)  # top 25
