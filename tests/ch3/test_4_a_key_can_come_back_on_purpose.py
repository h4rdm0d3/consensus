"""A key can come back on purpose."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch3_helpers import reopen


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
