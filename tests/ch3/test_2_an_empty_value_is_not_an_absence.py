"""An empty value is not an absence."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch3_helpers import reopen


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
