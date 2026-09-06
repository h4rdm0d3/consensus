"""Recover to a valid prefix."""

import random

from consensus.logfile import LogFile
from consensus.store import Store

from ch5_helpers import assert_is_a_prefix, build


def test_truncation_at_every_offset_recovers_prefix(tmp_path):
    # a crash can cut the file at any byte. Every one of them must open.
    src = build(str(tmp_path / "src.log"))
    whole = open(src, "rb").read()

    for cut in range(len(whole) + 1):
        p = str(tmp_path / f"cut_{cut}.log")
        with open(p, "wb") as f:
            f.write(whole[:cut])
        try:
            store = Store(LogFile(p))
        except Exception as e:
            raise AssertionError(
                f"truncating at byte {cut} of {len(whole)} made the store "
                f"unopenable: {type(e).__name__}: {e}"
            ) from None
        assert_is_a_prefix(store)
        store.close()


def test_garbage_tail_does_not_corrupt_prefix(tmp_path):
    p = build(str(tmp_path / "g.log"))
    before = Store(LogFile(p)).state_hash()

    rng = random.Random(1234)
    with open(p, "ab") as f:
        f.write(bytes(rng.randrange(256) for _ in range(200)))

    store = Store(LogFile(p))
    assert_is_a_prefix(store)
    assert store.state_hash() == before, "garbage after the last good record changed the state"


def test_recovery_is_idempotent(tmp_path):
    p = build(str(tmp_path / "i.log"))
    with open(p, "ab") as f:
        f.write(b"\x01\x02\x03")

    a = Store(LogFile(p)).state_hash()
    b = Store(LogFile(p)).state_hash()
    assert a == b, "opening the same damaged log twice gave two different states"


def test_writing_after_recovering_from_torn_tail(tmp_path):
    # recovery must leave the log in a state you can append to. If the torn
    # bytes are still there, the next record is written after garbage and the
    # log is permanently unreadable past that point.
    p = build(str(tmp_path / "w.log"))
    whole = open(p, "rb").read()
    with open(p, "wb") as f:
        f.write(whole[:-4])              # cut the last record in half

    store = Store(LogFile(p))
    recovered = sorted(store.keys())
    store.set("after", "recovery")
    store.close()

    reopened = Store(LogFile(p))
    assert reopened.get("after") == "recovery", (
        "a write made after recovery did not survive. The torn tail was never "
        "cleared, so the new record sits behind garbage"
    )
    assert sorted(reopened.keys()) == sorted(recovered + ["after"])
