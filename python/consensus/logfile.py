"""Chapter 1 · Easy — records on disk that can be read back.

The situation:
    A key-value store must survive restart, so every write is appended to a
    file. The previous version wrote each record as the key's bytes followed by
    the value's bytes, nothing else. `fixtures/mystery.log` is one such file.
    It holds three records. Recover them.

    (Do that first, by hand, before writing any code. Write down what you find.)

Your job:
    Design the record format so that recovery is possible at all, and implement
    the writer and the reader.

You may not:
    - use a serialization library that hides the boundary for you — no json,
      pickle, msgpack, protobuf, csv. You emit the bytes.
    - assume any byte or character cannot appear in a key or a value. Keys and
      values are arbitrary strings: empty, newlines, NULs, commas, quotes,
      emoji, anything.
    - rewrite or move bytes that were already written. Append only.
    - read the whole file and search for a parse that "works". Recovery is a
      single forward pass: at every point you must know where you are.

You may assume:
    - one process, one file, clean shutdown. Nothing crashes mid-write yet.
    - `str` keys and values.

The API:
    log = LogFile(path)
    log.append("k", "v")          # durable-ish; appends one record
    list(log.scan())              # -> [("k", "v"), ...] in write order
    log.close()

Make python/tests/test_ch01_framing.py go from red to green.
"""

import re
from collections.abc import Iterator
from contextlib import AbstractContextManager
from enum import StrEnum, auto
from io import BufferedReader
from pathlib import Path
from typing import Any

FIXED_WIDTH_KV_PTR = 8
HEADER_RE = re.compile(r"^kv;version=(?P<version>\d+);ksize=(?P<ksize>\d+);$")
HEADER_REF = "kv;version=1000000;ksize=64;"
HEADER_SIZE = len(HEADER_REF.encode("utf-8"))


class RecordState(StrEnum):
    PRESENT = auto()
    DELETED = auto()
    EOF = auto()


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


def read_bytes(f: BufferedReader, size: int) -> bytes:
    b = f.read(size)
    if len(b) < size:
        raise RuntimeError("[Corrupted value]: Value wasn't found.")
    return b


def read_key_with_header(f: BufferedReader) -> tuple[RecordState, bytes]:
    del_mask = f.read(1)
    record_state = RecordState.PRESENT
    match del_mask:
        case b"\x00":
            pass
        case b"\x01":
            record_state = RecordState.DELETED
        case b"":
            return RecordState.EOF, b""
        case _:
            raise ValueError(
                "[Corrupted record]: Invalid flag value for deletion mask."
            )

    size = f.read(FIXED_WIDTH_KV_PTR)
    if not size:
        raise RuntimeError("[Corrupted record]: Key marker missing.")

    if len(size) < FIXED_WIDTH_KV_PTR:
        raise RuntimeError("[Corrupted record]: Key not found.")
    return record_state, read_bytes(f, int.from_bytes(size, "little"))


def read_val_with_header(f: BufferedReader) -> tuple[RecordState, bytes]:
    size = f.read(FIXED_WIDTH_KV_PTR)
    if not size:
        raise RuntimeError("[Corrupted record]: Value marker missing.")

    if len(size) < FIXED_WIDTH_KV_PTR:
        raise RuntimeError("[Corrupted record]: Value marker wasn't found.")
    return RecordState.PRESENT, read_bytes(f, int.from_bytes(size, "little"))


def parse_header(hb: bytes) -> tuple[int, int]:
    try:
        header = hb.rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError:
        raise RuntimeError("Invalid file. Read aborted")
    m = HEADER_RE.match(header)
    if not m:
        raise RuntimeError("Invalid file - bad header. Read aborted")
    return int(m["version"]), int(m["ksize"])


class LogFile(AbstractContextManager):
    def __init__(self, path: str, version: int = 1, key_size: int = 32) -> None:
        self.path = Path(path)
        self.ksize = key_size
        self.version = version
        if self.path.exists() and self.path.stat().st_size > 0:
            with open(self.path, "rb") as f:
                hb = f.read(HEADER_SIZE)
                version, ksize = parse_header(hb)
                self.ksize = ksize
        else:
            header = f"kv;version={self.version};ksize={self.ksize};"
            hb = header.encode("utf-8")
            hb = hb.ljust(HEADER_SIZE, b"\x00")
            with open(self.path, "wb") as f:
                f.write(hb)
        self.rh = open(self.path, "rb")
        self.wh = open(self.path, "ab")

    def append(self, key: str, value: str, is_delete: bool = False) -> int:
        """Append one record. Chapter 2: return the offset it was written at."""
        offset = self.wh.tell()
        key_b = to_bytes(key)
        value_b = to_bytes(value)
        if is_delete:
            self.wh.write(b"\x01")
        else:
            self.wh.write(b"\x00")
        self.wh.write(to_bytes(len(key_b)))
        self.wh.write(key_b)
        self.wh.write(to_bytes(len(value_b)))
        self.wh.write(value_b)
        return offset

    # --- Chapter 2 additions -------------------------------------------------

    def read_at(self, offset: int) -> tuple[str, str]:
        """Read exactly the one record that starts at `offset`.

        Reads nothing before it and nothing after it.
        """
        self.wh.flush()
        self.rh.seek(offset)
        kstate, kb = read_key_with_header(self.rh)
        vstate, vb = read_val_with_header(self.rh)
        match (kstate, vstate):
            case RecordState.DELETED, _:
                raise DeletedRecordError(f"key={kb.decode('utf-8')} does not exist.")
            case RecordState.PRESENT, RecordState.PRESENT:
                return kb.decode("utf-8"), vb.decode("utf-8")
            case _, _:
                raise RuntimeError(
                    "[Corrupted Index]: No value metadata was found in the record."
                )

    def scan(self) -> Iterator[tuple[str, str | None]]:
        """Yield every record, in the order it was written."""
        if not self.wh.closed:
            self.wh.flush()
        with open(self.path, "rb") as f:
            f.seek(HEADER_SIZE)
            while True:
                kstate, kb = read_key_with_header(f)
                if kstate == RecordState.EOF:
                    return
                vstate, vb = read_val_with_header(f)
                match kstate, vstate:
                    case RecordState.DELETED, _:
                        yield kb.decode("utf-8"), None
                    case RecordState.PRESENT, RecordState.PRESENT:
                        yield kb.decode("utf-8"), vb.decode("utf-8")
                    case _, _:
                        continue

    def index_builder(self) -> Iterator[tuple[str, str, int, RecordState]]:
        """Yield every record, in the order it was written."""
        if not self.wh.closed:
            self.wh.flush()
        with open(self.path, "rb") as f:
            f.seek(HEADER_SIZE)
            while True:
                offset = f.tell()
                kstate, kb = read_key_with_header(f)
                if kstate == RecordState.EOF:
                    return
                vstate, vb = read_val_with_header(f)
                match kstate, vstate:
                    case RecordState.DELETED, _:
                        yield kb.decode("utf-8"), "", offset, RecordState.DELETED
                    case RecordState.PRESENT, RecordState.PRESENT:
                        yield (
                            kb.decode("utf-8"),
                            vb.decode("utf-8"),
                            offset,
                            RecordState.PRESENT,
                        )
                    case _, _:
                        continue

    def delete(self, k: str) -> None:
        self.append(k, "", is_delete=True)

    def __exit__(self, exc_typ, exc, tb):
        self.close()
        return False

    def close(self) -> None:
        self.wh.close()
        self.rh.close()
