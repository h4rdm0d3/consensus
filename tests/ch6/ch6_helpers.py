"""Shared by every segment of chapter 6."""

import os

from consensus.logfile import LogFile
from consensus.store import Store


def churn(path, keys=8, rounds=40):
    """A log where 8 keys are live and 312 records are dead."""
    s = Store(LogFile(path))
    for r in range(rounds):
        for k in range(keys):
            s.set(f"k{k}", f"v{r}")
    s.close()
    return path


def live_state(store):
    """Everything the store currently claims, as a plain dict."""
    return {k: store.get(k) for k in sorted(store.keys())}


def size(path):
    return os.path.getsize(path)
