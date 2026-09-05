# Chapter 3: The deleted key came back

*easy · single process, seeded faults, everything reproducible*

Oracle for Chapter 3 · Easy: recording absence.

Contract added this chapter:
    Store(log).delete(key) -> None    the key stops existing, permanently

Everything from Ch 1 and Ch 2 still holds: append-only, history preserved,
lookups touch one record, and a reopened Store recovers the same state.

Every test here kills a *plausible wrong* delete, not just an empty one:

```
- dropping the key from the in-memory index only -> key returns on restart
- writing an empty value to mean "deleted"       -> collides with real data
- rewriting or truncating the log                -> history destroyed
- a rebuild that ignores record order            -> resurrection
```

## Segments

| file | what it forces | tests |
| --- | --- | --- |
| `test_1_absence_must_persist.py` | Absence must persist | 3 |
| `test_2_empty_value_is_not_absence.py` | An empty value is not an absence | 2 |
| `test_3_delete_must_be_total.py` | Delete must be total | 2 |
| `test_4_key_can_come_back_on_purpose.py` | A key can come back on purpose | 2 |
| `test_5_what_replay_sees.py` | What replay sees | 4 |

## Running it

```
pytest tests/ch3/test_1_absence_must_persist.py   # one segment
pytest tests/ch3                                  # the whole chapter
pytest                                            # everything you have built so far
```
