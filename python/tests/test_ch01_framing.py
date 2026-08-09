"""Oracle for Chapter 1 · Easy — record framing on disk.

Contract:
    LogFile(path).append(key, value)     appends one record, never rewrites
    LogFile(path).scan()  -> Iterator[(key, value)] in write order

Every test here kills a *plausible wrong* format, not just an empty one:
    - key+value concatenated        -> roundtrip garbage (the mystery.log bug)
    - a delimiter byte (, : \\n \\0)  -> dies when the payload contains it
    - a character-count length      -> dies on multibyte (chars != bytes)
    - rewriting the file each time  -> dies on the append-only check
"""
import os
import random

import pytest

from consensus.logfile import LogFile


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "test.log")


def roundtrip(path, records):
    log = LogFile(path)
    for k, v in records:
        log.append(k, v)
    log.close()
    return list(LogFile(path).scan())


# Bytes and characters that break naive formats: classic delimiters, NUL,
# newlines, quotes, digits (length-prefix ambiguity), and multibyte.
NASTY = [
    "", "a", "1", "12", "0",
    "\x00", "\n", "\r\n", ",", ":", "|", "\t", " ",
    '"', "'", "\\", "=", "\x01",
    "é", "😀", "日本",
    "a\x00b", "1,2", "k=v", "\x00\x00", "a\nb",
]


def _payloads(seed, n):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        k = "".join(rng.choice(NASTY) for _ in range(rng.randint(0, 3)))
        v = "".join(rng.choice(NASTY) for _ in range(rng.randint(0, 3)))
        out.append((k, v))
    return out


def test_single_record_roundtrips(path):
    assert roundtrip(path, [("k", "v")]) == [("k", "v")]


def test_many_records_keep_write_order(path):
    records = [("a", "1"), ("b", "2"), ("c", "3")]
    assert roundtrip(path, records) == records


def test_empty_key_and_empty_value(path):
    # "" is a legal key and a legal value, and they are different from absent.
    records = [("", ""), ("k", ""), ("", "v")]
    assert roundtrip(path, records) == records


def test_the_mystery_log_case(path):
    # the exact records fixtures/mystery.log was built from. Concatenating
    # key+value with no boundary makes these unrecoverable; your format must
    # recover them exactly.
    records = [("a", "1"), ("b", "22"), ("cc", "3")]
    assert roundtrip(path, records) == records


@pytest.mark.parametrize("sep", ["\x00", "\n", ",", ":", "|", "\t", " ", "="])
def test_payload_may_contain_any_delimiter_you_picked(tmp_path, sep):
    # whatever byte you chose as a separator, a value is allowed to contain it.
    p = str(tmp_path / f"sep_{ord(sep)}.log")
    records = [("k" + sep + "1", sep), (sep * 3, "v" + sep)]
    assert roundtrip(p, records) == records, (
        f"format breaks when the payload contains {sep!r} — "
        "a delimiter made of legal payload bytes is not a boundary"
    )


def test_multibyte_payloads(path):
    # "é" is 1 character but 2 UTF-8 bytes; "😀" is 1 character but 4 bytes.
    # A length that counts characters will not match the bytes it frames.
    records = [("é", "😀"), ("日本語", "aé😀"), ("😀" * 5, "é" * 9)]
    assert roundtrip(path, records) == records, (
        "multibyte broke the framing — are you counting characters where you "
        "should count bytes?"
    )


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_adversarial_payloads_roundtrip(path, seed):
    records = _payloads(seed, 40)
    assert roundtrip(path, records) == records


def test_append_never_rewrites_earlier_bytes(path):
    # append-only: bytes already on disk must not move or change. This is what
    # makes a log recoverable, and later, replicable.
    log = LogFile(path)
    log.append("first", "record")
    log.close()
    prefix = open(path, "rb").read()

    log = LogFile(path)
    log.append("second", "record")
    log.close()
    after = open(path, "rb").read()

    assert after[: len(prefix)] == prefix, "appending rewrote earlier bytes"
    assert len(after) > len(prefix)


def test_reopening_recovers_everything(path):
    # the point of the exercise: state survives a restart.
    log = LogFile(path)
    log.append("k", "v")
    log.close()

    log = LogFile(path)
    log.append("k2", "v2")
    log.close()

    assert list(LogFile(path).scan()) == [("k", "v"), ("k2", "v2")]


def test_scan_on_a_fresh_file_is_empty(path):
    assert list(LogFile(path).scan()) == []


def test_scan_does_not_consume_the_log(path):
    # scanning is a read: doing it twice gives the same answer.
    log = LogFile(path)
    log.append("k", "v")
    log.close()
    reader = LogFile(path)
    assert list(reader.scan()) == list(reader.scan())
