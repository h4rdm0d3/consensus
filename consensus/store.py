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
        self.log = log
        self.index: dict[str, int] = {}
        self.build_index()

    def build_index(self) -> None:
        for k, _, offset in self.log.index_builder():
            self.index[k] = offset

    def set(self, key: str, value: str) -> None:
        offset = self.log.append(key, value)
        self.index[key] = offset

    def get(self, key: str) -> str | None:
        """The value written most recently for `key`, or None."""
        offset = self.index.get(key)
        if offset is not None:
            k, v = self.log.read_at(offset)
            return v
        return None

    def keys(self) -> Iterator[str]:
        """Every key that currently exists, once each."""
        for k in list(self.index.keys()):
            yield k

    # --- Chapter 3 ---------------------------------------------------------------------

    def delete(self, key: str) -> None:
        """Make `key` stop existing, permanently and across restarts.

        You cannot remove bytes from the middle of an append-only file, so
        absence has to be written down. Careful how you mark it: "" is a legal
        value and has been since Chapter 1.
        """
        raise NotImplementedError("Chapter 3: implement delete")

    def close(self) -> None:
        self.log.close()
