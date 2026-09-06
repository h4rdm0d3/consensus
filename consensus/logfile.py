"""Chapter 1 · Easy: records on disk that can be read back.

The situation:
    A key-value store must survive restarts. So it appends every write to a
    file. Where does one record end and the next begin?

You may not:
    - use a serialization library that hides the boundary for you. No json,
      pickle, msgpack, protobuf, csv. You emit the bytes.
    - assume any byte or character cannot appear in a key or a value. Keys and
      values are arbitrary strings: empty, newlines, NULs, commas, quotes,
      emoji, anything.
    - rewrite or move bytes that were already written. Append only.
    - read the whole file into memory. A log outgrows RAM long before it
      outgrows the disk.
    - try candidate splits until one parses. Recovery is one forward pass.

You may assume:
    - one process, one file, a clean shutdown.
    - `str` keys and values.

The API:
    log = LogFile(path)
    log.append("k", "v")          # appends one record
    list(log.scan())              # -> [("k", "v"), ...] in write order
    log.close()

Make the tests in tests/ch1/ go from red to green.
"""

import os
import struct
import zlib
from collections.abc import Iterator
from contextlib import AbstractContextManager
from enum import Enum, StrEnum, auto
from io import BufferedReader
from pathlib import Path
from typing import Any

FIXED_WIDTH_KV_PTR = 8
CRC_WIDTH = 4
VAL_MAX_SIZE = 1 << 32
ID_SIZE = 2
KEY_DESC = 1
VERSION_DESC = 4
HEADER_FMT = "<I2sIBB"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
HEADER_REDUNDANCY = 2
PROG_ID = b"kv"
PROG_ID_SIZE = len(PROG_ID)


class Flags(Enum):
    DELETE = b"\x11"
    PRESENT = b"\x01"


class RecordState(StrEnum):
    PRESENT = auto()
    DELETED = auto()
    EOF = auto()
    CORRUPTED = auto()


class DeletedRecordError(KeyError): ...


def to_bytes(t: Any) -> bytes:
    match t:
        case str():
            return t.encode("utf-8")
        case int():
            if t < 0:
                raise RuntimeError("Negative numbers are not expected")
            return t.to_bytes(FIXED_WIDTH_KV_PTR, "little", signed=False)
        case _ as typ:
            raise RuntimeError(f"Can't process {typ}.")


def read_bytes(f: BufferedReader, size: int) -> bytes | None:
    b = f.read(size)
    if len(b) < size:
        return None
    return b


def read_checksum(f: BufferedReader) -> tuple[RecordState, int]:
    crc_b = f.read(CRC_WIDTH)
    if not crc_b:
        return RecordState.EOF, 0
    if len(crc_b) < CRC_WIDTH:
        return RecordState.CORRUPTED, 0
    return RecordState.PRESENT, int.from_bytes(crc_b, "little")


def read_key_with_header(
    f: BufferedReader, max_ksize: int
) -> tuple[RecordState, bytes]:
    del_mask = f.read(1)
    record_state = RecordState.PRESENT
    match del_mask:
        case Flags.PRESENT.value:
            record_state = RecordState.PRESENT
        case Flags.DELETE.value:
            record_state = RecordState.DELETED
        case _:
            return RecordState.CORRUPTED, b""

    size = f.read(FIXED_WIDTH_KV_PTR)
    if not size:
        return RecordState.CORRUPTED, b""

    if len(size) < FIXED_WIDTH_KV_PTR:
        return RecordState.CORRUPTED, b""

    ksize = int.from_bytes(size, "little")
    if ksize > 1 << max_ksize:
        return RecordState.CORRUPTED, b""
    b = read_bytes(f, ksize)
    if b is None:
        return RecordState.CORRUPTED, b""
    return record_state, b


def read_val_with_header(f: BufferedReader, vsize: int) -> tuple[RecordState, bytes]:
    size = f.read(FIXED_WIDTH_KV_PTR)
    if not size:
        return RecordState.CORRUPTED, b""

    if len(size) < FIXED_WIDTH_KV_PTR:
        return RecordState.CORRUPTED, b""
    rec_vsize = int.from_bytes(size, "little")
    if rec_vsize > 1 << vsize:
        return RecordState.CORRUPTED, b""
    remaining = os.fstat(f.fileno()).st_size - f.tell()
    if rec_vsize > remaining:
        return RecordState.CORRUPTED, b""
    b = read_bytes(f, int.from_bytes(size, "little"))
    if b is None:
        return RecordState.CORRUPTED, b""
    return RecordState.PRESENT, b


class LogFile(AbstractContextManager):
    def __init__(
        self, path: str, version: int = 1, key_size: int = 16, val_size: int = 32
    ) -> None:
        self.path = Path(path)
        self.ksize = key_size
        self.vsize = val_size
        self.version = version
        state = RecordState.EOF
        if self.path.exists() and self.path.stat().st_size > 0:
            state, version, ksize, vsize = self.read_header()
            if state == RecordState.PRESENT:
                assert self.version == version
                self.ksize = ksize
                self.vsize = vsize
        if not self.path.exists() or state == RecordState.EOF:
            self.create_log()
        if state == RecordState.CORRUPTED:
            self.recover()
        self.rh = open(self.path, "rb")
        self.wh = open(self.path, "ab")

    def create_log(self, mode: str = "wb") -> None:
        id_ = "kv".encode("utf-8")
        version = self.version.to_bytes(4, "little")
        ksize = self.ksize.to_bytes(1, "little")
        vsize = self.vsize.to_bytes(1, "little")
        crc = zlib.crc32(id_)
        for part in (version, ksize, vsize):
            crc = zlib.crc32(part, crc)
        with open(self.path, mode) as f:
            if mode == "rb+":
                f.seek(0)
            for _ in range(HEADER_REDUNDANCY):
                f.write(crc.to_bytes(CRC_WIDTH, "little"))
                f.write("kv".encode("utf-8"))
                f.write(self.version.to_bytes(VERSION_DESC, "little"))
                f.write(self.ksize.to_bytes(1, "little"))
                f.write(self.vsize.to_bytes(1, "little"))

    def read_header(self) -> tuple[RecordState, int, int, int]:
        statuses = []
        with open(self.path, "rb") as f:
            for _ in range(HEADER_REDUNDANCY):
                hdr = f.read(HEADER_SIZE)
                statuses.append(self.header_status(hdr))
        for s in statuses:
            if s[0] != RecordState.CORRUPTED:
                return s
        return RecordState.CORRUPTED, -1, -1, -1

    def header_status(self, hdr: bytes) -> tuple[RecordState, int, int, int]:
        corrupted = RecordState.CORRUPTED, -1, -1, -1

        if len(hdr) < HEADER_SIZE:
            return (RecordState.EOF, -1, -1, -1)
        crc, id_, version, ksize, vsize = struct.unpack(HEADER_FMT, hdr)

        if crc != zlib.crc32(hdr[CRC_WIDTH:]):
            return corrupted

        if id_ != PROG_ID:
            return corrupted

        return RecordState.PRESENT, version, ksize, vsize

    def recover(self) -> None:
        n_records = sum(1 for _ in self.walk())
        if n_records > 0:
            self.create_log(mode="rb+")

    def append(self, key: str, value: str, is_delete: bool = False) -> int:
        """Append one record. Chapter 2: return the offset it was written at."""
        offset = self.wh.tell()
        key_b = to_bytes(key)
        value_b = to_bytes(value)

        flag = Flags.DELETE.value if is_delete else Flags.PRESENT.value
        if len(key_b) > 1 << self.ksize:
            raise ValueError(
                "KV Store is configured to expect max key "
                f"length to be {1 << self.ksize} but {1 << len(key_b)} was found."
            )
        if len(value_b) > 1 << self.vsize:
            raise ValueError(
                "KV Store is configured to expect max value "
                f"to be {1 << self.vsize} but {1 << len(key_b)} was found."
            )
        ksize = to_bytes(len(key_b))
        vsize = to_bytes(len(value_b))
        crc = zlib.crc32(flag)
        for part in (ksize, key_b, vsize, value_b):
            crc = zlib.crc32(part, crc)
        checksum = crc.to_bytes(CRC_WIDTH, "little")
        for part in (checksum, flag, ksize, key_b, vsize, value_b):
            self.wh.write(part)
        self.wh.flush()
        return offset

    # --- Chapter 2 additions -------------------------------------------------

    def read_at(self, offset: int) -> tuple[str, str]:
        """Read exactly the one record that starts at `offset`.

        Reads nothing before it and nothing after it.
        """
        self.wh.flush()
        self.rh.seek(offset)
        chkstate, actual = read_checksum(self.rh)
        kstate, kb = read_key_with_header(self.rh, self.ksize)
        vstate, vb = read_val_with_header(self.rh, self.vsize)
        match (chkstate, kstate, vstate):
            case RecordState.DELETED, _, _:
                raise DeletedRecordError(f"key={kb.decode('utf-8')} does not exist.")
            case RecordState.PRESENT, RecordState.PRESENT, RecordState.PRESENT:
                checksum = zlib.crc32(Flags.PRESENT.value)
                for part in (to_bytes(len(kb)), kb, to_bytes(len(vb)), vb):
                    checksum = zlib.crc32(part, checksum)
                if checksum != actual:
                    raise RuntimeError("[Corrupted record]: checksum mismatch")
                k, v = kb.decode("utf-8"), vb.decode("utf-8")
                return k, v
            case _, _, _:
                raise RuntimeError(
                    "[Corrupted Index]: No value metadata was found in the record."
                )

    def walk(self) -> Iterator[tuple[bytes, bytes | None]]:
        if not self.wh.closed:
            self.wh.flush()
        with open(self.path, "rb") as f:
            f.seek(HEADER_SIZE * HEADER_REDUNDANCY)
            while True:
                chkstate, actual = read_checksum(f)
                kstate, kb = read_key_with_header(f, self.ksize)
                vstate, vb = read_val_with_header(f, self.vsize)
                match chkstate, kstate, vstate:
                    case RecordState.EOF, _, _:
                        return
                    case RecordState.CORRUPTED, _, _:
                        return
                    case _, RecordState.CORRUPTED, _:
                        return
                    case _, _, RecordState.CORRUPTED:
                        return
                    case _, RecordState.DELETED, _:
                        yield kb, None
                    case RecordState.PRESENT, RecordState.PRESENT, RecordState.PRESENT:
                        checksum = zlib.crc32(Flags.PRESENT.value)
                        for part in (to_bytes(len(kb)), kb, to_bytes(len(vb)), vb):
                            checksum = zlib.crc32(part, checksum)
                        if checksum != actual:
                            continue
                        yield kb, vb

    def scan(self) -> Iterator[tuple[str, str | None]]:
        """Yield every record, in the order it was written."""
        if not self.wh.closed:
            self.wh.flush()
        with open(self.path, "rb") as f:
            f.seek(HEADER_SIZE * HEADER_REDUNDANCY)
            while True:
                offset = f.tell()
                chkstate, actual = read_checksum(f)
                kstate, kb = read_key_with_header(f, self.ksize)
                vstate, vb = read_val_with_header(f, self.vsize)
                match chkstate, kstate, vstate:
                    case RecordState.EOF, _, _:
                        return
                    case RecordState.CORRUPTED, _, _:
                        os.truncate(self.path, offset)
                        return
                    case _, RecordState.CORRUPTED, _:
                        os.truncate(self.path, offset)
                        return
                    case _, _, RecordState.CORRUPTED:
                        os.truncate(self.path, offset)
                        return
                    case _, RecordState.DELETED, _:
                        yield kb.decode("utf-8"), None
                    case RecordState.PRESENT, RecordState.PRESENT, RecordState.PRESENT:
                        checksum = zlib.crc32(Flags.PRESENT.value)
                        for part in (to_bytes(len(kb)), kb, to_bytes(len(vb)), vb):
                            checksum = zlib.crc32(part, checksum)
                        if checksum != actual:
                            continue
                        k, v = kb.decode("utf-8"), vb.decode("utf-8")
                        yield k, v

    def index_builder(self) -> Iterator[tuple[str, str, int, RecordState]]:
        """Yield every record, in the order it was written."""
        if not self.wh.closed:
            self.wh.flush()
        with open(self.path, "rb") as f:
            f.seek(HEADER_SIZE * HEADER_REDUNDANCY)
            while True:
                offset = f.tell()
                chkstate, actual = read_checksum(f)
                kstate, kb = read_key_with_header(f, self.ksize)
                vstate, vb = read_val_with_header(f, self.vsize)
                match chkstate, kstate, vstate:
                    case RecordState.EOF, _, _:
                        return
                    case RecordState.CORRUPTED, _, _:
                        os.truncate(self.path, offset)
                        return
                    case _, RecordState.CORRUPTED, _:
                        os.truncate(self.path, offset)
                        return
                    case _, _, RecordState.CORRUPTED:
                        os.truncate(self.path, offset)
                        return
                    case _, RecordState.DELETED, _:
                        yield kb.decode("utf-8"), "", offset, RecordState.DELETED
                    case _, RecordState.PRESENT, RecordState.PRESENT:
                        checksum = zlib.crc32(Flags.PRESENT.value)
                        for part in (to_bytes(len(kb)), kb, to_bytes(len(vb)), vb):
                            checksum = zlib.crc32(part, checksum)
                        if checksum != actual:
                            continue
                        k, v = kb.decode("utf-8"), vb.decode("utf-8")
                        yield k, v, offset, RecordState.PRESENT

    def delete(self, k: str) -> None:
        self.append(k, "", is_delete=True)

    def __exit__(self, exc_typ, exc, tb):
        self.close()
        return False

    def close(self) -> None:
        self.wh.close()
        self.rh.close()
