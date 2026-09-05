"""Different states, different fingerprints."""

from ch4_helpers import hash_of


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
