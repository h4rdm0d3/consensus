"""The header is data too."""

import os

import pytest

from consensus.logfile import LogFile
from consensus.store import Store

from ch5_helpers import build


def data_start(path):
    """How many bytes sit in front of the first record.

    Discovered, not imported. append() reports the offset it wrote at, so on a
    fresh log the first one reports exactly what the format puts in front of
    the data. A test that imported a constant instead would only ever damage
    what that constant covers, and would miss a second copy of the header
    living just past it.
    """
    log = LogFile(path)
    offset = log.append("probe", "probe")
    log.close()
    return offset


def test_damaged_header_never_destroys_log(tmp_path):
    # Every record in the log is intact and individually checksummed. A single
    # bad byte in front of them must not cost you any: refusing to open is a
    # correct answer, deleting the file is not.
    n = data_start(str(tmp_path / "probe.log"))
    for pos in range(n):
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
        assert after[n:] == original[n:], (
            f"corrupting header byte {pos} altered the records after the header"
        )


def test_destroyed_header_is_refused_not_guessed(tmp_path):
    # Every byte in front of the data replaced. Whatever the header held, a
    # magic, a version, a layout, none of it survives, so nothing is left to
    # say how the rest of the file should be read. Guessing is how a store
    # returns a value nobody wrote.
    #
    # A format with no header at all fails here, and that is the point: this is
    # what makes the header necessary rather than suggested.
    n = data_start(str(tmp_path / "probe.log"))
    p = str(tmp_path / "wrecked.log")
    build(p)
    size = os.path.getsize(p)

    damaged = bytearray(open(p, "rb").read())
    damaged[:n] = b"\xa5" * n
    with open(p, "wb") as f:
        f.write(bytes(damaged))

    with pytest.raises(Exception):
        Store(LogFile(p))

    assert os.path.getsize(p) == size, (
        "refusing a wrecked header destroyed the log. The records were intact"
    )


def test_format_version_from_future_is_refused(tmp_path):
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
