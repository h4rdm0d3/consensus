"""A format you did not write."""

from ch1_helpers import roundtrip


def test_mystery_log_case(path):
    # the exact records fixtures/mystery.log was built from. Concatenating
    # key+value with no boundary makes these unrecoverable. Your format must
    # recover them exactly.
    records = [("a", "1"), ("b", "22"), ("cc", "3")]
    assert roundtrip(path, records) == records
