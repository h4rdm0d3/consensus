"""A record that can prove itself."""

from consensus.logfile import HEADER_SIZE, LogFile
from consensus.store import Store

from ch5_helpers import assert_is_a_prefix, build


def test_flipped_byte_in_last_record_is_detected(tmp_path):
    # structure survives a flipped bit: lengths still parse, the record still
    # "decodes". Only something that ties the bytes together can catch it.
    p = build(str(tmp_path / "f.log"))
    data = bytearray(open(p, "rb").read())
    data[-1] ^= 0xFF                     # corrupt the last record's value
    with open(p, "wb") as f:
        f.write(bytes(data))

    store = Store(LogFile(p))
    assert store.get("k11") != "v1\xff", "a corrupted value was served as data"
    assert_is_a_prefix(store)


def test_zero_filled_tail_is_not_data(tmp_path):
    # crashed filesystems leave zeros. On this format they parse as a legal
    # empty record, so structure alone cannot reject them.
    p = build(str(tmp_path / "z.log"))
    before = Store(LogFile(p)).state_hash()

    with open(p, "ab") as f:
        f.write(b"\x00" * 34)      # an exact multiple of an empty record

    store = Store(LogFile(p))
    assert "" not in list(store.keys()), "a run of zero bytes became a key"
    assert store.state_hash() == before, "zero bytes changed the state"
