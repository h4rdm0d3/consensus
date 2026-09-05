"""Shared by every segment of chapter 5."""

import os

from consensus.logfile import HEADER_SIZE, LogFile
from consensus.store import Store


_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
