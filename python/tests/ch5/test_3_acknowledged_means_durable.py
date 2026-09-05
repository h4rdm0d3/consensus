"""Acknowledged means durable."""

import os
import pytest
import subprocess
import sys
import time

from consensus.logfile import HEADER_SIZE, LogFile
from consensus.store import Store

from ch5_helpers import _PKG_ROOT, _WRITER


@pytest.mark.parametrize("attempt", [1, 2, 3, 4, 5])


def test_acknowledged_writes_survive_kill_9(tmp_path, attempt):
    # a real process, killed for real, at a moment nobody chose.
    p = str(tmp_path / f"crash_{attempt}.log")
    env = {**os.environ, "PYTHONPATH": _PKG_ROOT}
    proc = subprocess.Popen(
        [sys.executable, _WRITER, p],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    time.sleep(0.05 * attempt)
    proc.kill()
    out, err = proc.communicate(timeout=10)

    acked = [int(line) for line in out.split()]
    assert acked, f"the writer acknowledged nothing before dying: {err[-400:]}"

    store = Store(LogFile(p))
    for i in acked:
        assert store.get("k%06d" % i) == "v%06d" % i, (
            f"write {i} was acknowledged and then lost in a crash "
            f"({len(acked)} acknowledged in total)"
        )
