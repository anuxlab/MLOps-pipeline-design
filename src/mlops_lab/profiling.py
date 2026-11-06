import os
import platform
import time
from contextlib import contextmanager

try:
    import psutil
except ImportError:  # pragma: no cover - fallback for minimal environments
    psutil = None


@contextmanager
def profile_execution():
    process = psutil.Process(os.getpid()) if psutil else None
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    rss_before = process.memory_info().rss if process else None
    result = {}
    try:
        yield result
    finally:
        result.update({
            "wall_time_seconds": round(time.perf_counter() - wall_start, 6),
            "process_cpu_time_seconds": round(time.process_time() - cpu_start, 6),
            "rss_before_bytes": int(rss_before) if rss_before is not None else None,
            "rss_after_bytes": int(process.memory_info().rss) if process else None,
            "peak_rss_bytes": int(resource_peak_rss_bytes()) if psutil else None,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count_logical": os.cpu_count(),
        })


def resource_peak_rss_bytes():
    # ru_maxrss is KB on Linux and bytes on macOS.
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if platform.system() == "Darwin" else value * 1024
