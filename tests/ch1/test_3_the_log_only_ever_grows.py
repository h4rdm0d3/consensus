"""The log only ever grows."""

from consensus.logfile import LogFile


def test_append_never_rewrites_earlier_bytes(path):
    # append-only: bytes already on disk must not move or change. This is what
    # makes a log recoverable, and later, replicable.
    log = LogFile(path)
    log.append("first", "record")
    log.close()
    prefix = open(path, "rb").read()

    log = LogFile(path)
    log.append("second", "record")
    log.close()
    after = open(path, "rb").read()

    assert after[: len(prefix)] == prefix, "appending rewrote earlier bytes"
    assert len(after) > len(prefix)


def test_scan_does_not_consume_the_log(path):
    # scanning is a read: doing it twice gives the same answer.
    log = LogFile(path)
    log.append("k", "v")
    log.close()
    reader = LogFile(path)
    assert list(reader.scan()) == list(reader.scan())


def test_reopening_recovers_everything(path):
    # the point of the exercise: state survives a restart.
    log = LogFile(path)
    log.append("k", "v")
    log.close()

    log = LogFile(path)
    log.append("k2", "v2")
    log.close()

    assert list(LogFile(path).scan()) == [("k", "v"), ("k2", "v2")]
