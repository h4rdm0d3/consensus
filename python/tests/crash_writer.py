"""Helper for Chapter 5's crash test. Not a test module.

Writes records forever. After each set() returns, it acknowledges that write on
stdout — the same thing a server does when it tells a client "saved". The parent
kills this process at an arbitrary moment and then checks that every
acknowledged write is still there.
"""
import sys

from consensus.logfile import LogFile
from consensus.store import Store

path = sys.argv[1]
store = Store(LogFile(path))

i = 0
while True:
    store.set("k%06d" % i, "v%06d" % i)
    sys.stdout.write("%d\n" % i)
    sys.stdout.flush()
    i += 1
