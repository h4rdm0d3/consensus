"""Shared by every segment of chapter 4."""

import os

from consensus.logfile import LogFile
from consensus.store import Store


_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build(path, ops):
    """ops: ("set", k, v) | ("del", k). Returns the closed store's hash."""
    s = Store(LogFile(path))
    for op in ops:
        s.delete(op[1]) if op[0] == "del" else s.set(op[1], op[2])
    h = s.state_hash()
    s.close()
    return h


def hash_of(tmp_path, name, ops):
    return build(str(tmp_path / name), ops)
