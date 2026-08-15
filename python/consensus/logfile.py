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

from collections.abc import Iterator
from contextlib import AbstractContextManager
from io import BufferedReader
from pathlib import Path
from typing import Any

FIXED_WIDTH_KV_PTR = 8


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
        raise RuntimeError("Corrupted value")
    return b


def read_with_header(f: BufferedReader) -> bytes | None:
    size = f.read(FIXED_WIDTH_KV_PTR)
    if not size:
        return

    if len(size) < FIXED_WIDTH_KV_PTR:
        raise RuntimeError("Corrupted index!")
    return read_bytes(f, int.from_bytes(size, "little"))


class LogFile(AbstractContextManager):
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.f = open(self.path, "ab")

    def append(self, key: str, value: str) -> int:
        """Append one record. Chapter 2: return the offset it was written at."""
        key_b = to_bytes(key)
        value_b = to_bytes(value)
        self.f.write(to_bytes(len(key_b)))
        self.f.write(key_b)
        self.f.write(to_bytes(len(value_b)))
        self.f.write(value_b)

    # --- Chapter 2 additions -------------------------------------------------

    def read_at(self, offset: int) -> tuple[str, str]:
        """Read exactly the one record that starts at `offset`.

        Reads nothing before it and nothing after it.
        """
        raise NotImplementedError("Chapter 2: implement read_at")

    def scan(self) -> Iterator[tuple[str, str]]:
        """Yield every record, in the order it was written."""
        if not self.f.closed:
            self.f.flush()
        with open(self.path, "rb") as f:
            while True:
                key_b = read_with_header(f)
                if key_b is None:
                    return None
                val_b = read_with_header(f)
                if val_b is None:
                    raise RuntimeError(f"Invalid value for key={key_b}")
                yield key_b.decode("utf-8"), val_b.decode("utf-8")

    def __exit__(self, exc_typ, exc, tb):
        self.close()
        return False

    def close(self) -> None:
        self.f.close()
