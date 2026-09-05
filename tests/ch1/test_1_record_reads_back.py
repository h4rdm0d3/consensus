"""Record reads back."""

from consensus.logfile import LogFile

from ch1_helpers import roundtrip


def test_single_record_roundtrips(path):
    assert roundtrip(path, [("k", "v")]) == [("k", "v")]


def test_scan_on_fresh_file_is_empty(path):
    assert list(LogFile(path).scan()) == []


def test_many_records_keep_write_order(path):
    records = [("a", "1"), ("b", "2"), ("c", "3")]
    assert roundtrip(path, records) == records
