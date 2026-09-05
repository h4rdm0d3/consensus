"""The latest write wins."""

from consensus.logfile import LogFile
from consensus.store import Store


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
