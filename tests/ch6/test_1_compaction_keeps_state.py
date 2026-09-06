"""Compaction keeps the state."""

from consensus.logfile import LogFile
from consensus.store import Store

from ch6_helpers import churn, live_state


def test_state_is_unchanged(tmp_path):
    p = churn(str(tmp_path / "a.log"))
    s = Store(LogFile(p))
    before = live_state(s)
    s.compact()
    assert live_state(s) == before, (
        "compaction changed what the store answers. It may drop records, "
        "never answers"
    )


def test_fingerprint_is_unchanged(tmp_path):
    # chapter 4 built a fingerprint so a rebuild could be proved equal to what
    # it replaced. This is the first time it earns its keep.
    p = churn(str(tmp_path / "b.log"))
    s = Store(LogFile(p))
    before = s.state_hash()
    s.compact()
    assert s.state_hash() == before, (
        "the state after compaction is not the state before it"
    )


def test_state_survives_reopen(tmp_path):
    p = churn(str(tmp_path / "c.log"))
    s = Store(LogFile(p))
    before = live_state(s)
    s.compact()
    s.close()

    assert live_state(Store(LogFile(p))) == before, (
        "the compacted log does not read back. A rewritten file still has to "
        "be a log this store can open"
    )


def test_writing_after_compaction(tmp_path):
    p = churn(str(tmp_path / "d.log"))
    s = Store(LogFile(p))
    s.compact()
    s.set("fresh", "1")
    s.set("k0", "later")
    s.close()

    s2 = Store(LogFile(p))
    assert s2.get("fresh") == "1", "a write after compaction did not survive"
    assert s2.get("k0") == "later", "an overwrite after compaction did not survive"
