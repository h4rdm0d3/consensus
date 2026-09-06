"""A crash during compaction loses nothing."""

import os
import subprocess
import sys
import time

import pytest

from consensus.logfile import LogFile
from consensus.store import Store

from ch6_helpers import churn, live_state

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_COMPACTOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_compactor.py")


@pytest.mark.parametrize("attempt", [1, 2, 3, 4, 5])
def test_killed_mid_compaction_the_store_still_opens(tmp_path, attempt):
    # compaction rewrites the whole file. A crash in the middle of that is the
    # one moment where every record is in play at once, and the old file is
    # the only copy of anything not yet rewritten.
    p = churn(str(tmp_path / f"a{attempt}.log"), keys=6, rounds=30)
    expected = live_state(Store(LogFile(p)))

    proc = subprocess.Popen(
        [sys.executable, _COMPACTOR, p],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": _ROOT},
    )
    acked = []
    deadline = time.time() + 5
    while time.time() < deadline and len(acked) < attempt * 3:
        line = proc.stdout.readline()
        if not line:
            break
        acked.append(line.strip())
    proc.kill()
    _, err = proc.communicate()

    assert acked and acked[0] == "compacted", (
        f"the compactor never finished a compaction, so nothing was tested. "
        f"It printed {acked!r} and said: {err.strip().splitlines()[-1:] or ['nothing']}"
    )
    assert len(acked) > 1, "the compactor never acknowledged a write after compacting"

    s = Store(LogFile(p))
    for k, v in expected.items():
        assert s.get(k) == v, (
            f"{k} was durable before compaction started and reads back as "
            f"{s.get(k)!r}. A crash during compaction lost a committed record"
        )
    for k in acked[1:]:
        assert s.get(k) is not None, (
            f"{k} was acknowledged after compaction and is gone"
        )


def test_a_leftover_file_does_not_confuse_the_next_open(tmp_path):
    # a compaction that writes elsewhere and swaps leaves a partial file behind
    # when it dies. Opening the store must ignore it, whatever it is called.
    p = churn(str(tmp_path / "b.log"), keys=4, rounds=10)
    s = Store(LogFile(p))
    s.compact()
    s.close()
    expected = live_state(Store(LogFile(p)))

    for junk in ("b.log.compact", "b.log.tmp", "b.log.new", "b.log.1"):
        with open(tmp_path / junk, "wb") as f:
            f.write(b"\xa5" * 400)

    assert live_state(Store(LogFile(p))) == expected, (
        "a leftover file from an interrupted compaction changed what the "
        "store reads back"
    )
