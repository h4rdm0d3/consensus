"""Oracle for Chapter 4 · Easy — proving recovery reproduced the state.

Contract added this chapter:
    Store(log).state_hash() -> str

A fingerprint of the store's *logical state*: the set of live keys and their
current values. Nothing else may reach it — not the history that produced the
state, not where records happen to sit in the file, not the order keys were
first written, not which process is asking.

Note the contrast with scan(), which Chapter 3 required to be injective over
*histories*. This is the opposite job: two different histories that arrive at
the same state MUST produce the same hash, or the fingerprint cannot be used to
answer "do these two stores agree?"

Every test here kills a *plausible wrong* fingerprint:
    - hashing the index (offsets)      -> history leaks in
    - hashing in dict order            -> insertion order leaks in
    - key + value with no framing      -> distinct states collide
    - hash() or set iteration          -> the process's hash seed leaks in
"""
import json
import os
import subprocess
import sys

import pytest

from consensus.logfile import LogFile
from consensus.store import Store

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "store.log")


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


def test_insertion_order_does_not_reach_the_hash(tmp_path):
    a = hash_of(tmp_path, "a.log", [("set", "x", "1"), ("set", "y", "2")])
    b = hash_of(tmp_path, "b.log", [("set", "y", "2"), ("set", "x", "1")])
    assert a == b, "the order keys were first written leaked into the hash"


def test_history_does_not_reach_the_hash(tmp_path):
    # same final state, three different paths to it. A fingerprint that hashes
    # the index hashes offsets, and offsets are a fact about history.
    end = [("set", "a", "1"), ("set", "b", "2")]
    a = hash_of(tmp_path, "a.log", end)
    b = hash_of(tmp_path, "b.log", [("set", "a", "9"), ("set", "b", "2"), ("set", "a", "1")])
    c = hash_of(tmp_path, "c.log", [("set", "z", "0"), ("del", "z")] + end)
    assert a == b, "an overwritten value changed the hash of an identical state"
    assert a == c, "a deleted key still contributes to the hash"


def test_a_different_value_changes_the_hash(tmp_path):
    a = hash_of(tmp_path, "a.log", [("set", "k", "1")])
    b = hash_of(tmp_path, "b.log", [("set", "k", "2")])
    assert a != b


def test_a_different_key_changes_the_hash(tmp_path):
    a = hash_of(tmp_path, "a.log", [("set", "k1", "v")])
    b = hash_of(tmp_path, "b.log", [("set", "k2", "v")])
    assert a != b


def test_an_extra_key_changes_the_hash(tmp_path):
    a = hash_of(tmp_path, "a.log", [("set", "k", "v")])
    b = hash_of(tmp_path, "b.log", [("set", "k", "v"), ("set", "j", "w")])
    assert a != b


def test_an_empty_value_is_not_an_absent_key(tmp_path):
    a = hash_of(tmp_path, "a.log", [("set", "k", "")])
    b = hash_of(tmp_path, "b.log", [])
    assert a != b, "a key holding \"\" hashed the same as no key at all"


def test_no_framing_collision_in_the_hash(tmp_path):
    # Chapter 1's lesson, now inside the fingerprint: concatenating key and
    # value with no boundary makes {"a": "bb"} and {"ab": "b"} identical.
    a = hash_of(tmp_path, "a.log", [("set", "a", "bb")])
    b = hash_of(tmp_path, "b.log", [("set", "ab", "b")])
    assert a != b, "key/value boundary is not encoded in the hash"


def test_hash_does_not_depend_on_the_process(tmp_path):
    # PYTHONHASHSEED randomises str hashing and set iteration per process. A
    # fingerprint that depends on it cannot compare two machines — which is the
    # only thing a fingerprint is for.
    ops = [["set", "a", "1"], ["set", "b", "2"], ["del", "a"], ["set", "c", "3"]]
    p = str(tmp_path / "seed.log")
    build(p, [tuple(o) for o in ops])

    code = (
        "import sys; from consensus.logfile import LogFile; "
        "from consensus.store import Store; "
        "print(Store(LogFile(sys.argv[1])).state_hash())"
    )

    def run(seed):
        r = subprocess.run(
            [sys.executable, "-c", code, p],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONPATH": _PKG_ROOT},
        )
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    assert run(0) == run(1), (
        "the hash changes with PYTHONHASHSEED — you are hashing an unordered "
        "iteration, or calling hash()"
    )


def test_agreement_between_two_independently_built_stores(tmp_path):
    # the real use: two stores that took different routes must be comparable.
    a = hash_of(tmp_path, "a.log", [
        ("set", "x", "1"), ("set", "y", "2"), ("set", "x", "3"),
        ("del", "y"), ("set", "y", "2"), ("set", "z", ""),
    ])
    b = hash_of(tmp_path, "b.log", [
        ("set", "z", ""), ("set", "y", "2"), ("set", "x", "3"),
    ])
    assert a == b, "two stores in the same state disagreed about their state"
