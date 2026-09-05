"""A fingerprint is a pure observation."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch4_helpers import hash_of


def test_hash_is_a_pure_observation(path):
    s = Store(LogFile(path))
    s.set("a", "1")
    assert s.state_hash() == s.state_hash(), "reading the hash changed it"


def test_empty_store_is_stable(tmp_path):
    a = hash_of(tmp_path, "a.log", [])
    b = hash_of(tmp_path, "b.log", [])
    assert a == b


def test_hash_survives_a_restart(path):
    # the reason this chapter exists: prove recovery rebuilt the same state.
    s = Store(LogFile(path))
    for i in range(50):
        s.set(f"k{i}", f"v{i}")
    s.delete("k7")
    before = s.state_hash()
    s.close()

    assert Store(LogFile(path)).state_hash() == before, (
        "the state after replay is not the state you had before the restart"
    )
