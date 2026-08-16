"""Chapter 2 · Easy — two values for the same key.

The situation:
    Your log works. You set k=1. Later you set k=2. Both records are on disk —
    the second append did not overwrite the first, because nothing in an
    append-only file ever overwrites anything.

    Someone asks for k. Answer them.

    Then answer them again with ten million records in the log, without reading
    ten million records.

Your job:
    Build the store that sits on top of the log: set, get, and the list of keys
    that currently exist.

You may not:
    - sort, rewrite, or move anything already in the log. Still append-only.
    - keep values in memory. The store must hold more data than fits in RAM;
      whatever you remember about a key must be small and fixed-size.
    - read records you did not need. A lookup touches one record.
    - lose history. Every version ever written stays in the log.

You may assume:
    - one process, clean shutdown, no crashes yet.
    - the set of keys is small enough to fit in memory, even though the values
      are not. (This is a real engineering assumption with a real cost — the
      debrief will name what it buys and what it forbids.)

The API:
    store = Store(LogFile(path))
    store.set("k", "v")
    store.get("k")            # -> "v", or None if the key is not there
    sorted(store.keys())      # -> the keys that currently exist
    store.close()

    Store(LogFile(path))      # on an existing file, recovers everything

Make python/tests/test_ch02_index.py go from red to green.
"""

from collections.abc import Iterator

from consensus.logfile import DeletedRecordError, LogFile, RecordState


class Store:
    def __init__(self, log: LogFile) -> None:
        self.log = log
        self.index: dict[str, int] = {}
        self.build_index()

    def build_index(self) -> None:
        for k, _, offset, state in self.log.index_builder():
            match state, k in self.index:
                case RecordState.DELETED, True:
                    del self.index[k]
                case RecordState.PRESENT, _:
                    self.index[k] = offset

    def set(self, key: str, value: str) -> None:
        offset = self.log.append(key, value)
        self.index[key] = offset

    def get(self, key: str) -> str | None:
        """The value written most recently for `key`, or None."""
        offset = self.index.get(key)
        if offset is not None:
            try:
                _, v = self.log.read_at(offset)
                return v
            except DeletedRecordError:
                return None
        return None

    def keys(self) -> Iterator[str]:
        """Every key that currently exists — each one once."""
        for k in list(self.index.keys()):
            yield k

    def delete(self, k: str) -> None:
        if k in self.index:
            del self.index[k]
        self.log.delete(k)

    def close(self) -> None:
        self.log.close()
