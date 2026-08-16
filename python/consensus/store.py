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
        """Every key that currently exists — each one once."""
        raise NotImplementedError("Chapter 2: implement keys")

    # --- Chapter 3 -----------------------------------------------------------

    def delete(self, key: str) -> None:
        """Make `key` stop existing — permanently, across restarts.

        You cannot remove bytes from the middle of an append-only file, so
        absence has to be written down. Careful how you mark it: "" is a legal
        value and has been since Chapter 1.
        """
        raise NotImplementedError("Chapter 3: implement delete")

    # --- Chapter 4 -----------------------------------------------------------

    def state_hash(self) -> str:
        """A fingerprint of the store's logical state.

        Live keys and their current values, and nothing else — not the history
        that produced them, not where records sit in the file, not the order
        keys were first written, not which process is asking.

        Note the contrast with scan(), which Chapter 3 required to be injective
        over histories. This is the opposite job: two stores that arrived at the
        same state by different routes must agree.
        """
        raise NotImplementedError("Chapter 4: implement state_hash")

    def close(self) -> None:
        raise NotImplementedError("Chapter 2: implement close")
