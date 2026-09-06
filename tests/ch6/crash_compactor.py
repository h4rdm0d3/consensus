"""Helper for chapter 6's crash test. Not a test module.

Compacts a log and then keeps writing, acknowledging each write on stdout the
way a server tells a client "saved". The parent kills this process at an
arbitrary moment and checks that the store still opens and that every
acknowledged write is still there.
"""

import sys

from consensus.logfile import LogFile
from consensus.store import Store

path = sys.argv[1]
store = Store(LogFile(path))
store.compact()
print("compacted", flush=True)

i = 0
while True:
    store.set(f"after{i}", str(i))
    print(f"after{i}", flush=True)
    i += 1
