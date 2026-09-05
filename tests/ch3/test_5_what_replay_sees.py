"""What replay sees."""

import random

import pytest

from consensus.logfile import LogFile
from consensus.store import Store

from ch3_helpers import reopen
from tests.ch2.ch2_helpers import CountingLog   # chapter 2's instrument


def test_delete_appends_and_never_rewrites(path):
    s = Store(LogFile(path))
    s.set("k", "v")
    s.close()
    before = open(path, "rb").read()

    s = Store(LogFile(path))
    s.delete("k")
    s.close()
    after = open(path, "rb").read()

    assert after[: len(before)] == before, "delete rewrote bytes already on disk"
    assert len(after) > len(before), "delete wrote nothing. Absence must be recorded"


def test_a_deleted_key_costs_no_record_read(path):
    # a deleted key is a miss, and a miss reads nothing (Chapter 2's rule).
    log = CountingLog(LogFile(path))
    s = Store(log)
    s.set("k", "v")
    s.delete("k")

    before_reads, before_scans = log.reads, log.scans
    assert s.get("k") is None
    assert log.reads == before_reads, "a deleted key should not read a record"
    assert log.scans == before_scans, "a deleted key should not walk the log"


def test_scan_records_what_actually_happened(tmp_path):
    # scan() is a history view. Chapter 2 fixed that: every version a key ever
    # had is reported, in order. So it must be injective over histories: three
    # logs that differ must render differently. Anything that rebuilds a log
    # from scan() (compaction, replication, backup) depends on this.
    #
    #   A: set k="v", delete k   -> k does not exist
    #   B: set k="v", set k=""   -> k exists, empty value
    #   C: set k="v"             -> k exists, "v"
    #
    # Rendering a tombstone as ""  collapses A into B.
    # Omitting the tombstone entirely collapses A into C.
    def build(name, ops):
        p = str(tmp_path / name)
        s = Store(LogFile(p))
        for op in ops:
            s.delete(op[0]) if len(op) == 1 else s.set(*op)
        s.close()
        return p

    pa = build("a.log", [("k", "v"), ("k",)])
    pb = build("b.log", [("k", "v"), ("k", "")])
    pc = build("c.log", [("k", "v")])

    assert Store(LogFile(pa)).get("k") is None
    assert Store(LogFile(pb)).get("k") == ""
    assert Store(LogFile(pc)).get("k") == "v"

    sa, sb, sc = (list(LogFile(p).scan()) for p in (pa, pb, pc))
    assert sa != sb, (
        "scan() renders a tombstone the same as an empty-string write. The "
        "record kind survives on disk but is discarded at the API"
    )
    assert sa != sc, (
        "scan() omits the tombstone, so a deleted key is indistinguishable "
        "from one that was never deleted. A compactor would resurrect it"
    )
    assert sb != sc


@pytest.mark.parametrize("seed", [1, 2, 3, 4])


def test_matches_a_plain_dict_across_restarts(path, seed):
    # the store, restarted at random moments, must agree with a dict that was
    # never written to disk at all.
    rng = random.Random(seed)
    model: dict[str, str] = {}
    keyspace = "abcde"
    values = ["", "1", "2", "x" * 40]

    s = Store(LogFile(path))
    for _ in range(200):
        k = rng.choice(keyspace)
        if rng.random() < 0.3:
            s.delete(k)
            model.pop(k, None)
        else:
            v = rng.choice(values)
            s.set(k, v)
            model[k] = v
        if rng.random() < 0.1:
            s.close()
            s = Store(LogFile(path))
    s.close()

    final = reopen(path)
    assert {k: final.get(k) for k in keyspace} == {k: model.get(k) for k in keyspace}
    assert sorted(final.keys()) == sorted(model)
