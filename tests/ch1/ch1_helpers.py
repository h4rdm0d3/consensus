"""Shared by every segment of chapter 1."""

import random

from consensus.logfile import LogFile


def roundtrip(path, records):
    log = LogFile(path)
    for k, v in records:
        log.append(k, v)
    log.close()
    return list(LogFile(path).scan())


NASTY = [
    "", "a", "1", "12", "0",
    "\x00", "\n", "\r\n", ",", ":", "|", "\t", " ",
    '"', "'", "\\", "=", "\x01",
    "é", "😀", "日本",
    "a\x00b", "1,2", "k=v", "\x00\x00", "a\nb",
]


def _payloads(seed, n):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        k = "".join(rng.choice(NASTY) for _ in range(rng.randint(0, 3)))
        v = "".join(rng.choice(NASTY) for _ in range(rng.randint(0, 3)))
        out.append((k, v))
    return out
