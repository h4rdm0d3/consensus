# Chapter 6: Restart takes an hour and the file never stops growing

*hard · real processes, real fsync, real kill -9*

Oracle for Chapter 6 · Hard: reclaiming space without losing anything.

Contract added this chapter:

    Store(log).compact() -> None    drop records that no longer matter

Everything from chapters 1 to 5 still holds. The log is append-only during
normal writes, a lookup costs one record read, replay rebuilds the same state,
and a crash at any byte offset loses nothing that was acknowledged.

Compaction is the one operation allowed to rewrite the file. That is what makes
it dangerous:

```
- dropping a tombstone            -> the key it hid comes back
- keeping the first record        -> a stale value wins
- rewriting in place              -> a crash halfway loses both copies
- forgetting to rebuild the index -> every offset now points at the wrong record
```

## Segments

| file | what it forces | tests |
| --- | --- | --- |
| `test_1_compaction_keeps_state.py` | Compaction keeps the state | 4 |
| `test_2_compaction_reclaims_space.py` | Compaction reclaims space | 3 |
| `test_3_deleted_keys_stay_deleted.py` | Deleted keys stay deleted | 4 |
| `test_4_a_crash_during_compaction_loses_nothing.py` | A crash during compaction loses nothing | 6 |
| `test_5_lookups_still_cost_one_read.py` | Lookups still cost one read | 3 |

## Running it

```
pytest tests/ch6/test_1_compaction_keeps_state.py   # one segment
pytest tests/ch6                                    # the whole chapter
pytest                                              # everything you have built so far
```
