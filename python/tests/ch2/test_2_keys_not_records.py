"""Keys, not records."""

from consensus.logfile import LogFile
from consensus.store import Store


def test_keys_lists_each_key_once(path):
    s = Store(LogFile(path))
    s.set("a", "1")
    s.set("b", "1")
    s.set("a", "2")
    assert sorted(s.keys()) == ["a", "b"], "keys() is reporting records, not keys"
