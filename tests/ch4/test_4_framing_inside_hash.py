"""Framing again, inside the hash."""

from ch4_helpers import hash_of


def test_no_framing_collision_in_hash(tmp_path):
    # Chapter 1's lesson, now inside the fingerprint: concatenating key and
    # value with no boundary makes {"a": "bb"} and {"ab": "b"} identical.
    a = hash_of(tmp_path, "a.log", [("set", "a", "bb")])
    b = hash_of(tmp_path, "b.log", [("set", "ab", "b")])
    assert a != b, "key/value boundary is not encoded in the hash"
