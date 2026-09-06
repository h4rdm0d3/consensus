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