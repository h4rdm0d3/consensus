"""Payloads that break your framing."""

import pytest

from ch1_helpers import _payloads, roundtrip


def test_empty_key_and_empty_value(path):
    # "" is a legal key and a legal value, and they are different from absent.
    records = [("", ""), ("k", ""), ("", "v")]
    assert roundtrip(path, records) == records


@pytest.mark.parametrize("sep", ["\x00", "\n", ",", ":", "|", "\t", " ", "="])


def test_payload_may_contain_any_delimiter_you_picked(tmp_path, sep):
    # whatever byte you chose as a separator, a value is allowed to contain it.
    p = str(tmp_path / f"sep_{ord(sep)}.log")
    records = [("k" + sep + "1", sep), (sep * 3, "v" + sep)]
    assert roundtrip(p, records) == records, (
        f"format breaks when the payload contains {sep!r}. "
        "A delimiter made of legal payload bytes is not a boundary"
    )


def test_multibyte_payloads(path):
    # "é" is 1 character but 2 UTF-8 bytes. "😀" is 1 character but 4 bytes.
    # A length that counts characters will not match the bytes it frames.
    records = [("é", "😀"), ("日本語", "aé😀"), ("😀" * 5, "é" * 9)]
    assert roundtrip(path, records) == records, (
        "multibyte broke the framing. Are you counting characters where you "
        "should count bytes?"
    )


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])


def test_adversarial_payloads_roundtrip(path, seed):
    records = _payloads(seed, 40)
    assert roundtrip(path, records) == records
