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

## Three tiers per chapter

| Tier | What it is | Language |
| --- | --- | --- |
| **Easy** | Single process, clean restarts, faults you inject by hand, everything seeded. Build the intuition. | Python |
| **Hard** | Real processes, sockets, `fsync`, clock drift, `kill -9`. No mocks. The scheduler is the adversary. | Rust |
| **Impossible** | The same correct system at a target a naive-correct build can't hit. Safety invariants are the gate. | Rust |

The Easy oracle must still pass at Hard. Every safety invariant must still pass
at Impossible. The oracle is the through-line.

## Chapters

**Part I — The Log** (single node, on disk). The file *is* a write-ahead log;
the index *is* a state machine.
1. The file won't read back ← *start here*
2. Two values for the same key
3. The deleted key came back
4. Replay gives a different answer
5. The last record is half there
6. Restart takes an hour

**Part II — The Wire** · 7. Two messages arrived glued together · 8. The reply was for a request you already retried · 9. The instrument

**Part III — Failure and Time** · 10. The node wasn't dead, it was slow · 11. The reply arrived before the message · 12. Two leaders, one slot, different values

**Part IV — The Algorithm** · 13. Agree on one value, and never change it · 14. Two round-trips per value won't scale · 15. Never two leaders in a term · 16. Index 7 disagrees · 17. A stale leader ate a durable write

**Part V — Making It Real** · 18. Recovery takes an hour, and a new node can never catch up · 19. You added two nodes and got two leaders again · 20. The withdrawal ran twice; the read was stale · 21. You can't eyeball a 10k-op history

**Part VI — Proving It** · 22. Failed once in CI, never again · 23. Your tests only run on a healthy network · 24. Passing tests, or untested cases? · 25. Correct and 50× too slow

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
