"""Deleted keys stay deleted."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch6_helpers import live_state


def test_a_deleted_key_does_not_come_back(tmp_path):
    # the chapter. Compaction drops records that no longer matter, and the
    # record that says "gone" looks exactly like one that no longer matters.
    p = str(tmp_path / "a.log")
    s = Store(LogFile(p))
    s.set("k", "v")
    s.delete("k")
    s.compact()
    s.close()

    assert Store(LogFile(p)).get("k") is None, (
        "the deleted key came back. Compaction dropped the tombstone and the "
        "record it was hiding"
    )


def test_a_deleted_key_stays_out_of_keys(tmp_path):
    p = str(tmp_path / "b.log")
    s = Store(LogFile(p))
    for i in range(5):
        s.set(f"k{i}", str(i))
    s.delete("k2")
    s.compact()
    s.close()

    assert sorted(Store(LogFile(p)).keys()) == ["k0", "k1", "k3", "k4"]


def test_delete_then_set_survives_compaction(tmp_path):
    # order still decides. A key deleted and written again is live, and the
    # value it must have is the later one.
    p = str(tmp_path / "c.log")
    s = Store(LogFile(p))
    s.set("k", "old")
    s.delete("k")
    s.set("k", "new")
    s.compact()
    s.close()

    assert Store(LogFile(p)).get("k") == "new", (
        "compaction kept the wrong record for a key that was deleted and "
        "written again"
    )


def test_many_deletes_leave_nothing_behind(tmp_path):
    p = str(tmp_path / "d.log")
    s = Store(LogFile(p))
    for i in range(30):
        s.set(f"k{i}", str(i))
    for i in range(30):
        s.delete(f"k{i}")
    before = live_state(s)
    s.compact()
    s.close()

    s2 = Store(LogFile(p))
    assert live_state(s2) == before == {}, "an emptied store did not stay empty"
    assert sorted(s2.keys()) == []
