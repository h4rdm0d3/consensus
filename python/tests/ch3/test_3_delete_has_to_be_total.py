"""Delete has to be total."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch3_helpers import reopen


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
