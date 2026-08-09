# hardmode · consensus

Build a replicated state machine out of its own failures.

This is not a how-to-build-Raft course — those exist. This one is about **why
these systems are built exactly the way they are**: the forces that make each
design decision inevitable, so you can re-derive a protocol you've forgotten and
evaluate one you've never seen.

Each chapter is a system that **already broke**: a concrete symptom, a list of
things you're **forbidden** from doing (so the cheap fix is closed off), and an
executable **oracle** that goes red first. You make it green.

The oracle is written to fail a *plausible wrong* answer, not just an empty one.
If a naive solution passes everything, the oracle is broken — open an issue.

## Difficulty

Each chapter is written once, at the difficulty its scope demands. The ramp
comes from the sequence — build the simple model, then a later chapter exposes
it to the harder form of the same problem.

| | What it means | Stack |
| --- | --- | --- |
| 🟢 **Easy** | Single process, clean restarts, logical time, seeded faults. Everything reproducible. Models get built here. | Python |
| 🟡 **Hard** | Real processes, sockets, `fsync`, clock drift, `kill -9`. No mocks; the scheduler is the adversary. | Python |
| 🔴 **Impossible** | A target a naive-correct build can't hit. Profile, then move the measured hot path to Rust behind the same API. | Python + Rust (PyO3/maturin) |

Nondeterminism is a property of the environment, not the language — Hard stays
in Python. **Rust is an outcome of measurement, never a premise:** profile
first, extract only the hot path, keep the pure-Python implementation so both
can be benchmarked A/B, and re-run the whole oracle against the native path.
Sometimes the honest answer is a better algorithm or `mmap`, not Rust.

## Chapters

**Part I — The Log** (single node, on disk). The file *is* a write-ahead log;
the index *is* a state machine.
1. 🟢 The file won't read back ← *start here*
2. 🟢 Two values for the same key
3. 🟢 The deleted key came back
4. 🟢 Replay gives a different answer
5. 🟡 The last record is half there
6. 🟡 Restart takes an hour and the file never stops growing
7. 🔴 fsync costs 10 ms and you need 50k writes/sec

**Part II — The Wire** · 8. 🟢 The instrument · 9. 🟡 Two messages arrived glued together · 10. 🟡 The reply was for a request you already retried

**Part III — Failure and Time** · 11. 🟢 The node wasn't dead, it was slow · 12. 🟢 The reply arrived before the message · 13. 🟢 Two leaders, one slot, different values

**Part IV — The Algorithm** (in the simulator) · 14. 🟢 Agree on one value, and never change it · 15. 🟢 Two round-trips per value won't scale · 16. 🟢 Never two leaders in a term · 17. 🟢 Index 7 disagrees · 18. 🟢 A stale leader ate a durable write

**Part V — Reality** · 19. 🟡 Five processes, five sockets, one `kill -9` · 20. 🟡 Recovery takes an hour, and a new node can never catch up · 21. 🟡 You added two nodes and got two leaders again · 22. 🟡 The withdrawal ran twice; the read was stale · 23. 🟡 You can't eyeball a 10k-op history · 24. 🟡 Your tests only run on a healthy network

**Part VI — Proof and the Frontier** · 25. 🟢 Failed once in CI, never again · 26. 🟢 Passing tests, or untested cases? · 27. 🔴 Correct and 50× too slow

## Global invariants

Election safety · log matching · leader completeness · state-machine safety ·
determinism (same command sequence ⇒ same state hash, every node, every run) ·
durability (anything acknowledged survives a crash at any byte offset).

A performance change that regresses any of these is a regression, not a speedup.

## Start

```sh
cd python
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest -q          # red until you implement the stubs
```

Chapter 1 begins in `python/consensus/logfile.py` — read the docstring, then
open `python/fixtures/mystery.log` and try to recover the three records it
holds. Do that by hand before writing code.
