"""Absence must persist."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch3_helpers import reopen


def test_delete_removes_key(path):
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
        "the deleted key came back. Absence was never written down"
    )


def test_deleted_key_is_not_listed(path):
    s = Store(LogFile(path))
    s.set("a", "1")
    s.set("b", "2")
    s.delete("a")
    assert sorted(s.keys()) == ["b"]
    s.close()
    assert sorted(reopen(path).keys()) == ["b"]
