"""Oracle for Chapter 3 · Easy — recording absence.

Contract added this chapter:
    Store(log).delete(key) -> None    the key stops existing, permanently

Everything from Ch 1 and Ch 2 still holds: append-only, history preserved,
lookups touch one record, and a reopened Store recovers the same state.

Every test here kills a *plausible wrong* delete, not just an empty one:
    - dropping the key from the in-memory index only -> key returns on restart
    - writing an empty value to mean "deleted"       -> collides with real data
    - rewriting or truncating the log                -> history destroyed
    - a rebuild that ignores record order            -> resurrection
"""
import random

import pytest

from consensus.logfile import LogFile
from consensus.store import Store


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "store.log")


def reopen(path):
    return Store(LogFile(path))


def test_delete_removes_the_key(path):
    s = Store(LogFile(path))
    s.set("k", "v")
    s.delete("k")
    assert s.get("k") is None


def test_delete_survives_restart(path):
    # the whole chapter. An in-memory-only delete passes the test above and
    # fails this one: the original record is still in the log.
    s = Store(LogFile(path))
    s.set("k", "v")
    s.delete("k")
    s.close()

    assert reopen(path).get("k") is None, (
        "the deleted key came back — absence was never written down"
    )


def test_deleted_key_is_not_listed(path):
    s = Store(LogFile(path))
    s.set("a", "1")
    s.set("b", "2")
    s.delete("a")
    assert sorted(s.keys()) == ["b"]
    s.close()
    assert sorted(reopen(path).keys()) == ["b"]


def test_empty_value_is_not_a_deletion(path):
    # "" is a legal value and has been since Chapter 1. A tombstone marked by
    # an empty value cannot tell them apart.
    s = Store(LogFile(path))
    s.set("k", "")
    s.close()

    s2 = reopen(path)
    assert s2.get("k") == "", "an empty value was mistaken for a deletion"
    assert sorted(s2.keys()) == ["k"]


def test_empty_value_written_after_a_delete(path):
    s = Store(LogFile(path))
    s.set("k", "v")
    s.delete("k")
    s.set("k", "")
    s.close()

    s2 = reopen(path)
    assert s2.get("k") == "", "the later empty-string write should have revived the key"
    assert sorted(s2.keys()) == ["k"]


def test_delete_of_an_absent_key_is_a_noop(path):
    s = Store(LogFile(path))
    s.delete("never-set")
    assert s.get("never-set") is None
    assert sorted(s.keys()) == []
    s.close()
    assert sorted(reopen(path).keys()) == []


def test_deleting_twice_is_a_noop(path):
    s = Store(LogFile(path))
    s.set("k", "v")
    s.delete("k")
    s.delete("k")
    s.close()
    assert reopen(path).get("k") is None


def test_set_after_delete_resurrects_the_key(path):
    s = Store(LogFile(path))
    s.set("k", "1")
    s.delete("k")
    s.set("k", "2")
    assert s.get("k") == "2"
    s.close()

    s2 = reopen(path)
    assert s2.get("k") == "2", "rebuild ignored record order — the tombstone won"
    assert sorted(s2.keys()) == ["k"]


def test_delete_after_set_after_delete(path):
    s = Store(LogFile(path))
    for op in ["set", "del", "set", "del"]:
        s.set("k", "v") if op == "set" else s.delete("k")
    s.close()
    assert reopen(path).get("k") is None


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
    assert len(after) > len(before), "delete wrote nothing — absence must be recorded"


def test_a_deleted_key_costs_no_record_read(path):
    # a deleted key is a miss, and a miss reads nothing (Chapter 2's rule).
    from tests.test_ch02_index import CountingLog

    log = CountingLog(LogFile(path))
    s = Store(log)
    s.set("k", "v")
    s.delete("k")

    before_reads, before_scans = log.reads, log.scans
    assert s.get("k") is None
    assert log.reads == before_reads, "a deleted key should not read a record"
    assert log.scans == before_scans, "a deleted key should not walk the log"


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
