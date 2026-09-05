"""Shared by every segment of chapter 2."""

from consensus.logfile import LogFile


class CountingLog:
    """A LogFile that records how the store touches the disk.

    scans -> how many times the whole log was walked. Any method whose name
             starts with "scan" counts, so you are free to add your own
             offset-reporting variant alongside scan().
    reads -> how many single records were read at a known offset
    """

    def __init__(self, log: LogFile) -> None:
        self._log = log
        self.scans = 0
        self.reads = 0

    def append(self, key: str, value: str) -> int:
        return self._log.append(key, value)

    def read_at(self, offset: int):
        self.reads += 1
        return self._log.read_at(offset)

    def close(self) -> None:
        self._log.close()

    def __getattr__(self, name):
        # anything else is proxied straight through; walks of the whole log
        # are counted whatever you decided to call them.
        attr = getattr(self._log, name)
        if name.startswith("scan"):

            def counted(*args, **kwargs):
                self.scans += 1
                yield from attr(*args, **kwargs)

            return counted
        return attr
