"""Oracle for Chapter 2 · Easy — the current value, found without scanning.

Contract:
    Store(log).set(k, v)      appends; never overwrites
    Store(log).get(k)         -> the most recently written value, or None
    Store(log).keys()         -> the keys that currently exist, each once
    Store(LogFile(path))      on an existing file, recovers everything

Every test here kills a *plausible wrong* store, not just an empty one:
    - returning the FIRST match in the log   -> stale value after an update
    - scanning the log on every get          -> correct but O(n): caught by counters
    - caching values in memory               -> caught: get must read from disk
    - a rebuild that keeps the earlier record -> caught after reopen
    - keys() built from raw records          -> duplicates
"""
import pytest

from consensus.logfile import LogFile
from consensus.store import Store


class CountingLog:
    """A LogFile that records how the store touches the disk.

    scans -> how many times the whole log was walked. Any method whose name
             starts with "scan" counts, so you are free to add your own
             offset-reporting variant alongside scan().
    reads -> how many single records were read at a known offset
    """

    def __init__(self, log: LogFile) -> None:
        self._log = log
        self.scans = 0
        self.reads = 0

    def append(self, key: str, value: str) -> int:
        return self._log.append(key, value)

    def read_at(self, offset: int):
        self.reads += 1
        return self._log.read_at(offset)

    def close(self) -> None:
        self._log.close()

    def __getattr__(self, name):
        # anything else is proxied straight through; walks of the whole log
        # are counted whatever you decided to call them.
        attr = getattr(self._log, name)
        if name.startswith("scan"):

            def counted(*args, **kwargs):
                self.scans += 1
                yield from attr(*args, **kwargs)

            return counted
        return attr


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "store.log")


def test_get_returns_the_most_recent_value(path):
    s = Store(LogFile(path))
    s.set("k", "1")
    s.set("k", "2")
    assert s.get("k") == "2", "returned a stale version — later records win"


def test_get_absent_key_is_none(path):
    assert Store(LogFile(path)).get("nope") is None


def test_stored_empty_string_is_not_absence(path):
    s = Store(LogFile(path))
    s.set("k", "")
    assert s.get("k") == ""
    assert s.get("missing") is None


def test_many_updates_to_one_key(path):
    s = Store(LogFile(path))
    for i in range(50):
        s.set("k", str(i))
    assert s.get("k") == "49"


def test_keys_lists_each_key_once(path):
    s = Store(LogFile(path))
    s.set("a", "1")
    s.set("b", "1")
    s.set("a", "2")
    assert sorted(s.keys()) == ["a", "b"], "keys() is reporting records, not keys"


def test_reopening_recovers_every_key(path):
    s = Store(LogFile(path))
    s.set("a", "1")
    s.set("b", "2")
    s.close()

    s2 = Store(LogFile(path))
    assert s2.get("a") == "1"
    assert s2.get("b") == "2"
    assert sorted(s2.keys()) == ["a", "b"]


def test_reopening_recovers_the_latest_version(path):
    # the rebuild must respect log order: later records overwrite earlier ones.
    s = Store(LogFile(path))
    s.set("k", "old")
    s.set("k", "new")
    s.close()

    assert Store(LogFile(path)).get("k") == "new", (
        "rebuild kept the earlier record — order is what decides the current value"
    )


def test_writes_survive_across_several_sessions(path):
    for i in range(3):
        s = Store(LogFile(path))
        s.set("k", str(i))
        s.set(f"k{i}", str(i))
        s.close()

    s = Store(LogFile(path))
    assert s.get("k") == "2"
    assert sorted(s.keys()) == ["k", "k0", "k1", "k2"]


def test_history_is_never_destroyed(path):
    # the store updates a key; the log still holds every version ever written.
    s = Store(LogFile(path))
    s.set("k", "1")
    s.set("k", "2")
    s.set("k", "3")
    s.close()

    assert list(LogFile(path).scan()) == [("k", "1"), ("k", "2"), ("k", "3")], (
        "the log lost history — the store must append, never rewrite"
    )


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
