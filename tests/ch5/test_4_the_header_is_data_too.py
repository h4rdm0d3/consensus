"""The header is data too."""

import os

import pytest

from consensus.logfile import HEADER_SIZE, LogFile
from consensus.store import Store

from ch5_helpers import build


def test_a_damaged_header_never_destroys_the_log(tmp_path):
    # Every record in the log is intact and individually checksummed. A single
    # bad byte in the 12-byte header must not cost you any of them: refusing to
    # open is a correct answer, deleting the file is not.
    for pos in range(HEADER_SIZE):
        p = str(tmp_path / f"hdr_{pos}.log")
        build(p)
        original = open(p, "rb").read()

        damaged = bytearray(original)
        damaged[pos] ^= 0xFF
        with open(p, "wb") as f:
            f.write(bytes(damaged))

        try:
            Store(LogFile(p))
        except Exception:
            pass                       # refusing is fine, destroying is not

        after = open(p, "rb").read()
        assert len(after) >= len(original), (
            f"corrupting header byte {pos} shrank the log from {len(original)} "
            f"to {len(after)} bytes. Every record in it was intact"
        )
        assert after[HEADER_SIZE:] == original[HEADER_SIZE:], (
            f"corrupting header byte {pos} altered the records after the header"
        )


def test_every_header_byte_is_covered_by_its_checksum(tmp_path):
    # A checksum that under-covers still verifies, so the only way to know it
    # covers the whole header is to corrupt each byte and demand it is noticed.
    missed = []
    for pos in range(HEADER_SIZE):
        p = str(tmp_path / f"cov_{pos}.log")
        build(p)
        damaged = bytearray(open(p, "rb").read())
        damaged[pos] ^= 0xFF
        with open(p, "wb") as f:
            f.write(bytes(damaged))
        try:
            Store(LogFile(p))
            missed.append(pos)
        except Exception:
            pass
    assert not missed, (
        f"header bytes {missed} can be corrupted without being detected. "
        "They are outside what the header checksum covers"
    )


def test_a_format_version_from_the_future_is_refused(tmp_path):
    # The version field exists so an older build refuses a newer format instead
    # of misreading it. A log written as v99 must not be opened by this build.
    p = str(tmp_path / "v99.log")
    log = LogFile(p, version=99)
    log.append("k", "v")
    log.close()
    size = os.path.getsize(p)

    with pytest.raises(Exception):
        Store(LogFile(p))

    assert os.path.getsize(p) == size, "refusing a future version destroyed the log"
