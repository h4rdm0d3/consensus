"""Lookup must not walk the log."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch2_helpers import CountingLog


def test_get_does_not_walk_the_log(path):
    # the whole point: lookup cost must not grow with the size of the log.
    log = CountingLog(LogFile(path))
    s = Store(log)
    for i in range(500):
        s.set(f"k{i}", str(i))

    before = log.scans
    for i in range(500):
        assert s.get(f"k{i}") == str(i)
    assert log.scans == before, (
        f"get() walked the log {log.scans - before} times — that is O(n) per lookup"
    )


def test_get_reads_exactly_one_record_from_disk(path):
    # values live on disk, not in memory: a hit must cost one targeted read.
    log = CountingLog(LogFile(path))
    s = Store(log)
    s.set("a", "1")
    s.set("b", "2")

    before = log.reads
    assert s.get("a") == "1"
    assert log.reads == before + 1, (
        f"get() performed {log.reads - before} record reads; expected exactly 1 "
        "(0 means the value was cached in memory — values must stay on disk)"
    )


def test_missing_key_touches_no_records(path):
    log = CountingLog(LogFile(path))
    s = Store(log)
    s.set("a", "1")

    before_reads, before_scans = log.reads, log.scans
    assert s.get("nope") is None
    assert log.reads == before_reads, "a miss should not read any record"
    assert log.scans == before_scans, "a miss should not walk the log"


def test_recovery_walks_the_log_once(path):
    s = Store(LogFile(path))
    for i in range(100):
        s.set(f"k{i}", str(i))
    s.close()

    log = CountingLog(LogFile(path))
    s2 = Store(log)
    assert log.scans <= 1, (
        f"recovery walked the log {log.scans} times; once is enough"
    )
    assert s2.get("k42") == "42"
