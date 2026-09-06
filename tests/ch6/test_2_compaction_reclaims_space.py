"""Compaction reclaims space."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch6_helpers import churn, size


def test_a_log_of_garbage_shrinks(tmp_path):
    # 8 keys written 40 times each. 312 of the 320 records are dead.
    p = churn(str(tmp_path / "a.log"))
    before = size(p)
    s = Store(LogFile(p))
    s.compact()
    s.close()

    after = size(p)
    assert after < before / 4, (
        f"compaction took {before} bytes to {after}. Only 8 of 320 records "
        f"are live, so most of the file is garbage that should be gone"
    )


def test_a_log_with_nothing_dead_does_not_grow(tmp_path):
    # every record is live, so there is nothing to reclaim. Compaction is
    # allowed to do nothing, and is not allowed to make the file bigger.
    p = str(tmp_path / "b.log")
    s = Store(LogFile(p))
    for i in range(50):
        s.set(f"k{i}", f"v{i}")
    s.close()
    before = size(p)

    s = Store(LogFile(p))
    s.compact()
    s.close()
    assert size(p) <= before, (
        f"compacting a log with no dead records grew it from {before} to "
        f"{size(p)} bytes"
    )


def test_compaction_is_idempotent(tmp_path):
    p = churn(str(tmp_path / "c.log"))
    s = Store(LogFile(p))
    s.compact()
    once = size(p)
    s.compact()
    assert size(p) == once, (
        f"a second compaction changed the file from {once} to {size(p)} bytes. "
        f"There was nothing left to reclaim"
    )
