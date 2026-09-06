"""Chapter 2 · Easy: two values for the same key.

The situation:
    Your log works. You set k=1. Later you set k=2. Both records are on disk.

    Someone asks for k. Which record answers them?

    Now answer with ten million records in the log, without reading ten
    million records.

You may not:
    - sort, rewrite, or move anything already in the log. Still append-only.
    - keep values in memory. The store must hold more data than fits in RAM.
    - read records you did not need. A lookup touches one record.
    - lose history. Every version ever written stays in the log.

You may assume:
    - one process, one file, a clean shutdown.
    - the set of keys fits in memory, even though the values do not. That is an
      engineering choice, not a law, and it has a cost.

The API:
    store = Store(LogFile(path))
    store.set("k", "v")
    store.get("k")            # -> "v", or None if the key is not there
    sorted(store.keys())      # -> the keys that currently exist
    store.close()

    Store(LogFile(path))      # on an existing file, recovers everything

Make the tests in tests/ch2/ go from red to green.
"""

import hashlib
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
        """Every key that currently exists, once each."""
        for k in list(self.index.keys()):
            yield k

    def delete(self, k: str) -> None:
        if k in self.index:
            del self.index[k]
        self.log.delete(k)

    def state_hash(self) -> str:
        h = hashlib.sha256()
        for k in sorted(self.index):
            offset = self.index[k]
            _, v = self.log.read_at(offset)
            for x in (k, v):
                h.update(len(x.encode("utf-8")).to_bytes(8, "little"))
                h.update(x.encode("utf-8"))
        return h.hexdigest()

    def close(self) -> None:
        self.log.close()
