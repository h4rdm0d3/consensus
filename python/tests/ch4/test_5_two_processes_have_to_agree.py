"""Two processes have to agree."""

import os
import subprocess
import sys

from ch4_helpers import _PKG_ROOT, build, hash_of


def test_hash_does_not_depend_on_the_process(tmp_path):
    # PYTHONHASHSEED randomises str hashing and set iteration per process. A
    # fingerprint that depends on it cannot compare two machines — which is the
    # only thing a fingerprint is for.
    ops = [["set", "a", "1"], ["set", "b", "2"], ["del", "a"], ["set", "c", "3"]]
    p = str(tmp_path / "seed.log")
    build(p, [tuple(o) for o in ops])

    code = (
        "import sys; from consensus.logfile import LogFile; "
        "from consensus.store import Store; "
        "print(Store(LogFile(sys.argv[1])).state_hash())"
    )

    def run(seed):
        r = subprocess.run(
            [sys.executable, "-c", code, p],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONPATH": _PKG_ROOT},
        )
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    assert run(0) == run(1), (
        "the hash changes with PYTHONHASHSEED — you are hashing an unordered "
        "iteration, or calling hash()"
    )


def test_agreement_between_two_independently_built_stores(tmp_path):
    # the real use: two stores that took different routes must be comparable.
    a = hash_of(tmp_path, "a.log", [
        ("set", "x", "1"), ("set", "y", "2"), ("set", "x", "3"),
        ("del", "y"), ("set", "y", "2"), ("set", "z", ""),
    ])
    b = hash_of(tmp_path, "b.log", [
        ("set", "z", ""), ("set", "y", "2"), ("set", "x", "3"),
    ])
    assert a == b, "two stores in the same state disagreed about their state"
