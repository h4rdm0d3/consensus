"""Lookups still cost one read."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch6_helpers import churn
from tests.ch2.ch2_helpers import CountingLog   # chapter 2's instrument


def test_get_reads_one_record_after_compaction(tmp_path):
    # compaction moves every record, so every offset the index holds is now
    # wrong. Chapter 2's rule did not change: a hit costs one read.
    p = churn(str(tmp_path / "a.log"), keys=5, rounds=20)
    log = CountingLog(LogFile(p))
    s = Store(log)
    s.compact()

    before = log.reads
    assert s.get("k3") == "v19"
    assert log.reads == before + 1, (
        f"get() performed {log.reads - before} record reads after compaction. "
        f"The index was not rebuilt against the new offsets"
    )


def test_get_does_not_walk_the_log_after_compaction(tmp_path):
    p = churn(str(tmp_path / "b.log"), keys=5, rounds=20)
    log = CountingLog(LogFile(p))
    s = Store(log)
    s.compact()

    before = log.scans
    for k in range(5):
        assert s.get(f"k{k}") == "v19"
    assert log.scans == before, (
        f"get() walked the log {log.scans - before} times after compaction. "
        f"Rebuilding the index is a one-off, not a per-lookup cost"
    )


def test_reopening_a_compacted_log_walks_it_once(tmp_path):
    p = churn(str(tmp_path / "c.log"), keys=5, rounds=20)
    s = Store(LogFile(p))
    s.compact()
    s.close()

    log = CountingLog(LogFile(p))
    s2 = Store(log)
    assert log.scans <= 1, f"recovery walked the compacted log {log.scans} times"
    assert s2.get("k0") == "v19"
