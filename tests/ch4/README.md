# Chapter 4: Replay gives a different answer

*easy · single process, seeded faults, everything reproducible*

Oracle for Chapter 4 · Easy: proving recovery reproduced the state.

Contract added this chapter:
    Store(log).state_hash() -> str

A fingerprint of the store's *logical state*: the set of live keys and their
current values. Nothing else may reach it: not the history that produced the
state, not where records happen to sit in the file, not the order keys were
first written, not which process is asking.

Note the contrast with scan(). Chapter 3 required that to be injective over
*histories*. This is the opposite job: two different histories that arrive at
the same state MUST produce the same hash, or the fingerprint cannot be used to
answer "do these two stores agree?"

Every test here kills a *plausible wrong* fingerprint:

```
- hashing the index (offsets)      -> history leaks in
- hashing in dict order            -> insertion order leaks in
- key + value with no framing      -> distinct states collide
- hash() or set iteration          -> the process's hash seed leaks in
```

## Segments

| file | what it forces | tests |
| --- | --- | --- |
| `test_1_fingerprint_is_pure_observation.py` | A fingerprint is a pure observation | 3 |
| `test_2_fingerprint_history_agnostic.py` | The fingerprint is history agnostic | 2 |
| `test_3_different_states_different_fingerprints.py` | Different states, different fingerprints | 4 |
| `test_4_framing_inside_hash.py` | Framing again, inside the hash | 1 |
| `test_5_two_processes_must_agree.py` | Two processes must agree | 2 |

## Running it

```
pytest tests/ch4/test_1_fingerprint_is_pure_observation.py   # one segment
pytest tests/ch4                                             # the whole chapter
pytest                                                       # everything you have built so far
```
