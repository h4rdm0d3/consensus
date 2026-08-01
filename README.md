# hardmode · consensus

Build a replicated state machine out of its own failures. No lectures.

Each chapter is a system that **already broke**: a concrete symptom, a list of
things you're **forbidden** from doing (so the cheap fix is closed off), and an
executable **oracle** that goes red first. You make it green.

The oracle is written to fail a *plausible wrong answer*, not just an empty one.
If a naive solution passes everything, the oracle is broken — open an issue.

## Three tiers per chapter

| Tier | What it is | Language |
| --- | --- | --- |
| **Easy** | Single thread, logical time, a network you fully control, everything seeded. Turn vocabulary into intuition. | Python |
| **Hard** | Real processes, sockets, `fsync`, clock drift, `kill -9`. No mocks. The scheduler is the adversary. | Rust |
| **Impossible** | The same correct system at a latency/throughput target a naive-correct build can't hit. Safety invariants are the gate. | Rust |

The Easy oracle must still pass at Hard. Every safety invariant must still pass
at Impossible. The oracle is the through-line.

## Global invariants

Election safety · log matching · leader completeness · state-machine safety ·
determinism (same command sequence ⇒ same state hash, every node, every run) ·
durability (anything acknowledged survives a crash at any byte offset).

A performance change that regresses any of these is a regression, not a speedup.

## Chapters

**Part I — Substrate**
1. Replay gives a different answer — deterministic state machine ← *start here*
2. Two messages arrived glued together — codec + RPC
3. You acked the write, then it vanished — write-ahead log
4. The instrument — a network simulator you control

**Part II — Failure and Time** · 5. The node wasn't dead, it was slow · 6. The reply arrived before the message · 7. Two leaders, one slot, different values

**Part III — The Algorithm** · 8. Agree on one value, never change it · 9. Two round-trips per value won't scale · 10. Never two leaders in a term · 11. Index 7 disagrees · 12. A stale leader ate a durable write

**Part IV — Making It Real** · 13. Recovery takes an hour · 14. Two nodes added, two leaders again · 15. The withdrawal ran twice · 16. You can't eyeball a 10k-op history

**Part V — Proving It** · 17. Failed once in CI, never again · 18. Tests only run on a healthy network · 19. Passing tests, or untested cases? · 20. Correct and 50× too slow

## Run the Easy tier

```sh
cd python
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest -q          # red until you implement the stubs
```

Implement the stubs in `python/consensus/` until the oracle in `python/tests/`
is green. Then read the chapter debrief — never before.
