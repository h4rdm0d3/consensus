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
        """Chapter 2: read exactly the one record that starts at `offset`.

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
