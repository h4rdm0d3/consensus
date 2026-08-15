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


class LogFile:
    def __init__(self, path: str) -> None:
        raise NotImplementedError("Chapter 1: implement LogFile")

    def append(self, key: str, value: str) -> int:
        """Append one record. Chapter 2: return the offset it was written at."""
        raise NotImplementedError("Chapter 1: implement append")

    def read_at(self, offset: int) -> tuple[str, str]:
        """Chapter 2: read exactly the one record that starts at `offset`.

        Reads nothing before it and nothing after it.
        """
        raise NotImplementedError("Chapter 2: implement read_at")

    def scan(self) -> Iterator[tuple[str, str]]:
        """Yield every record, in the order it was written."""
        raise NotImplementedError("Chapter 1: implement scan")

    def close(self) -> None:
        raise NotImplementedError("Chapter 1: implement close")