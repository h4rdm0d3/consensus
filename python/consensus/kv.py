"""Chapter 1 · Easy — deterministic key-value state machine.

A command is a tuple:
    ("set", key, value)   |   ("del", key)          # key and value are str

The symptom you are fixing:
    Apply the same list of writes twice, hash the state twice, and the two
    hashes disagree. Nothing random ran. No clock was read.

Forbidden:
    - no wall-clock, environment, or global mutable state inside apply()
    - the iteration order of an unordered collection must not reach the hash
    - no unseeded randomness

apply is (state, command) -> state and nothing more. Commands arrive already
ordered and already decoded, single-threaded. The network does not exist yet.

Make python/tests/test_ch01_state_machine.py go from red to green.
"""


class KVStore:
    def __init__(self) -> None:
        raise NotImplementedError("Chapter 1: implement KVStore")

    def apply(self, cmd: tuple) -> None:
        """Apply one command: ('set', k, v) or ('del', k)."""
        raise NotImplementedError("Chapter 1: implement apply")

    def state_hash(self) -> str:
        """A hex digest that is a function of the logical state and nothing else."""
        raise NotImplementedError("Chapter 1: implement state_hash")