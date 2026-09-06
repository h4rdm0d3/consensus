"""scan() does not load the file."""

import os
import tracemalloc

from consensus.logfile import LogFile


def test_scan_does_not_load_file(tmp_path):
    # a log outgrows RAM long before it outgrows the disk, so scan() has to
    # stream. Reading the file and then splitting it is the shape this kills.
    p = str(tmp_path / "big.log")
    log = LogFile(p)
    for i in range(50_000):
        log.append(f"key{i}", "v" * 80)
    log.close()
    size = os.path.getsize(p)

    tracemalloc.start()
    n = sum(1 for _ in LogFile(p).scan())      # consume lazily, hold nothing
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert n == 50_000
    assert peak < size / 4, (
        f"scan() held {peak / 1e6:.1f} MB while reading a {size / 1e6:.1f} MB "
        f"log. It is buffering the file instead of streaming it"
    )
