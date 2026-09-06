"""Chapter 2 · Easy: two values for the same key.

The situation:
    Your log works. You set k=1. Later you set k=2. Both records are on disk.

    Someone asks for k. Which record answers them?

    Now answer with ten million records in the log, without reading ten
    million records.

You may not:
    - sort, rewrite, or move anything already in the log. Still append-only.
    - keep values in memory. The store must hold more data than fits in RAM.
    - read more than one record to answer a lookup. A hit reads exactly one
      record. A miss reads none.
    - lose history. Every version ever written stays in the log.

The API:
    store = Store(LogFile(path))
    store.set("k", "v")
    store.get("k")            # -> "v", or None if the key is not there
    sorted(store.keys())      # -> the keys that currently exist
    store.close()

    Store(LogFile(path))      # on an existing file, recovers everything

Make the tests in tests/ch2/ go from red to green.
"""

from collections.abc import Iterator

from consensus.logfile import LogFile


class Store:
    def __init__(self, log: LogFile) -> None:
        raise NotImplementedError("Chapter 2: implement Store")

    def set(self, key: str, value: str) -> None:
        raise NotImplementedError("Chapter 2: implement set")

    def get(self, key: str) -> str | None:
        """The value written most recently for `key`, or None."""
        raise NotImplementedError("Chapter 2: implement get")

    def keys(self) -> Iterator[str]:
        """Every key that currently exists, once each."""
        raise NotImplementedError("Chapter 2: implement keys")

    def close(self) -> None:
        raise NotImplementedError("Chapter 2: implement close")
