"""Oracle for Chapter 1 · Easy. Must go red before KVStore is implemented.

Each test is built to kill a *plausible wrong* implementation, not just an
empty one. Read the assertion messages when they fire — they name the trap.
"""
import json
import os
import subprocess
import sys

from consensus.kv import KVStore

# python/ — the dir that contains the `consensus` package, for subprocess imports.
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(log):
    s = KVStore()
    for c in log:
        s.apply(tuple(c))
    return s.state_hash()


def _hash_in_subprocess(log, hashseed):
    # PYTHONHASHSEED randomizes str hashing and set/frozenset iteration order
    # per process. If state_hash() walks a set/dict in hash order, or uses
    # hash(), two processes disagree — and your "deterministic" replay isn't.
    code = (
        "import json,sys; from consensus.kv import KVStore; "
        "log=json.load(sys.stdin); s=KVStore(); "
        "[s.apply(tuple(c)) for c in log]; print(s.state_hash())"
    )
    p = subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(log),
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONHASHSEED": str(hashseed), "PYTHONPATH": _PKG_ROOT},
    )
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


def test_replay_determinism_same_process():
    log = [("set", "a", "1"), ("set", "b", "2"), ("del", "a"), ("set", "b", "3")]
    assert run(log) == run(log)


def test_replay_determinism_across_hash_seeds():
    log = [("set", "a", "1"), ("set", "b", "2"), ("del", "a"), ("set", "b", "3")]
    assert _hash_in_subprocess(log, 0) == _hash_in_subprocess(log, 1), (
        "state hash depends on PYTHONHASHSEED — you're hashing an unordered iteration"
    )


def test_state_depends_only_on_logical_state():
    # independent keys, different insertion order, identical final map => same hash
    a = run([("set", "x", "1"), ("set", "y", "2")])
    b = run([("set", "y", "2"), ("set", "x", "1")])
    assert a == b, "hash depends on insertion order — canonicalize before hashing"


def test_order_is_observed():
    # same key twice: order decides the surviving value => hash MUST differ
    a = run([("set", "k", "1"), ("set", "k", "2")])
    b = run([("set", "k", "2"), ("set", "k", "1")])
    assert a != b, "hash can't see last-writer-wins ordering"


def test_delete_is_not_a_noop():
    a = run([("set", "k", "1"), ("del", "k")])
    b = run([("set", "k", "1")])
    assert a != b, "delete left the key present, or the hash can't see absence"


def test_empty_is_stable():
    assert KVStore().state_hash() == KVStore().state_hash()
