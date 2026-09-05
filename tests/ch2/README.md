# Chapter 2: Two values for the same key

*easy · single process, seeded faults, everything reproducible*

Oracle for Chapter 2 · Easy — the current value, found without scanning.

Contract:
    Store(log).set(k, v)      appends; never overwrites
    Store(log).get(k)         -> the most recently written value, or None
    Store(log).keys()         -> the keys that currently exist, each once
    Store(LogFile(path))      on an existing file, recovers everything

Every test here kills a *plausible wrong* store, not just an empty one:
    - returning the FIRST match in the log   -> stale value after an update
    - scanning the log on every get          -> correct but O(n): caught by counters
    - caching values in memory               -> caught: get must read from disk
    - a rebuild that keeps the earlier record -> caught after reopen
    - keys() built from raw records          -> duplicates

## Segments

| file | what it forces | tests |
| --- | --- | --- |
| `test_1_the_latest_write_wins.py` | The latest write wins | 4 |
| `test_2_keys_not_records.py` | Keys, not records | 1 |
| `test_3_the_log_is_the_truth_the_index_is_a_view.py` | The log is the truth, the index is a view | 4 |
| `test_4_lookup_must_not_walk_the_log.py` | Lookup must not walk the log | 4 |

## Running it

```
pytest tests/ch2/test_1_the_latest_write_wins.py   # one segment
pytest tests/ch2                                   # the whole chapter
pytest                                             # everything you have built so far
```
