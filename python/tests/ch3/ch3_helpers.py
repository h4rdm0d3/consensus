"""Shared by every segment of chapter 3."""

from consensus.logfile import LogFile
from consensus.store import Store


def reopen(path):
    return Store(LogFile(path))
