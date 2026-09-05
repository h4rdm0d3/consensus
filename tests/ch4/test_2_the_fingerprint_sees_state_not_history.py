"""The fingerprint sees state, not history."""

from ch4_helpers import hash_of


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
