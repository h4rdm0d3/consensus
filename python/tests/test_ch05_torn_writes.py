"""Oracle for Chapter 5 · Hard — surviving a crash mid-write.

Two contracts, both new:

  RECOVERY IS TOTAL.  Opening a log whose tail is damaged must succeed and
  yield a valid prefix — every record up to the last complete, intact one, and
  nothing after it. Damage at the end of a log is normal; it is what a crash
  looks like. A store that refuses to open is a store you have lost.

  DEBRIS IS NOT DATA.  A partial record, a zero-filled tail, or a flipped byte
  must never be mistaken for something you wrote. Structure alone cannot tell
  them apart: on this format a run of zero bytes parses as a perfectly legal
  empty record.

  AND THE OLD ONE STILL HOLDS.  Anything acknowledged survives.

Every test here kills a *plausible wrong* recovery:
    - raising on a torn tail        -> the store cannot be opened at all
    - trusting structure alone      -> zeros become a key
    - recovering but not truncating -> the next append extends the garbage
"""
import os
import random
import subprocess
import sys
import time

import pytest

from consensus.logfile import LogFile
from consensus.store import Store

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WRITER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_writer.py")

OPS = [(f"k{i}", f"v{i}") for i in range(12)]


def build(path, ops=OPS):
    s = Store(LogFile(path))
    for k, v in ops:
        s.set(k, v)
    s.close()
    return path


def assert_is_a_prefix(store, ops=OPS):
    """The recovered state must be the state after some prefix of `ops`."""
    keys = sorted(store.keys())
    n = len(keys)
    expected = {k: v for k, v in ops[:n]}
    assert set(keys) == set(expected), (
        f"recovered keys are not a prefix of what was written: {keys}"
    )
    for k, v in expected.items():
        assert store.get(k) == v, f"{k} recovered with the wrong value"


def test_truncation_at_every_offset_recovers_a_prefix(tmp_path):
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


def test_a_zero_filled_tail_is_not_data(tmp_path):
    # crashed filesystems leave zeros. On this format they parse as a legal
    # empty record, so structure alone cannot reject them.
    p = build(str(tmp_path / "z.log"))
    before = Store(LogFile(p)).state_hash()

    with open(p, "ab") as f:
        f.write(b"\x00" * 34)      # an exact multiple of an empty record

    store = Store(LogFile(p))
    assert "" not in list(store.keys()), "a run of zero bytes became a key"
    assert store.state_hash() == before, "zero bytes changed the state"


def test_a_garbage_tail_does_not_corrupt_the_prefix(tmp_path):
    p = build(str(tmp_path / "g.log"))
    before = Store(LogFile(p)).state_hash()

    rng = random.Random(1234)
    with open(p, "ab") as f:
        f.write(bytes(rng.randrange(256) for _ in range(200)))

    store = Store(LogFile(p))
    assert_is_a_prefix(store)
    assert store.state_hash() == before, "garbage after the last good record changed the state"


def test_a_flipped_byte_in_the_last_record_is_detected(tmp_path):
    # structure survives a bit flip: lengths still parse, the record still
    # "decodes". Only something that ties the bytes together can catch it.
    p = build(str(tmp_path / "f.log"))
    data = bytearray(open(p, "rb").read())
    data[-1] ^= 0xFF                     # corrupt the last record's value
    with open(p, "wb") as f:
        f.write(bytes(data))

    store = Store(LogFile(p))
    assert store.get("k11") != "v1\xff", "a corrupted value was served as data"
    assert_is_a_prefix(store)


def test_recovery_is_idempotent(tmp_path):
    p = build(str(tmp_path / "i.log"))
    with open(p, "ab") as f:
        f.write(b"\x01\x02\x03")

    a = Store(LogFile(p)).state_hash()
    b = Store(LogFile(p)).state_hash()
    assert a == b, "opening the same damaged log twice gave two different states"


def test_writing_after_recovering_from_a_torn_tail(tmp_path):
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
        "a write made after recovery did not survive — the torn tail was never "
        "cleared, so the new record sits behind garbage"
    )
    assert sorted(reopened.keys()) == sorted(recovered + ["after"])


@pytest.mark.parametrize("attempt", [1, 2, 3, 4, 5])
def test_acknowledged_writes_survive_kill_9(tmp_path, attempt):
    # a real process, killed for real, at a moment nobody chose.
    p = str(tmp_path / f"crash_{attempt}.log")
    env = {**os.environ, "PYTHONPATH": _PKG_ROOT}
    proc = subprocess.Popen(
        [sys.executable, _WRITER, p],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    time.sleep(0.05 * attempt)
    proc.kill()
    out, err = proc.communicate(timeout=10)

    acked = [int(line) for line in out.split()]
    assert acked, f"the writer acknowledged nothing before dying: {err[-400:]}"

    store = Store(LogFile(p))
    for i in acked:
        assert store.get("k%06d" % i) == "v%06d" % i, (
            f"write {i} was acknowledged and then lost in a crash "
            f"({len(acked)} acknowledged in total)"
        )
