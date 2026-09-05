"""The log is the truth, the index is a view."""

from consensus.logfile import LogFile
from consensus.store import Store


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
        "rebuild kept the earlier record. Order is what decides the current value"
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
    # the store updates a key. The log still holds every version ever written.
    s = Store(LogFile(path))
    s.set("k", "1")
    s.set("k", "2")
    s.set("k", "3")
    s.close()

    assert list(LogFile(path).scan()) == [("k", "1"), ("k", "2"), ("k", "3")], (
        "the log lost history. The store must append, never rewrite"
    )
