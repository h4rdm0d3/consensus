# Chapter 5: The last record is half there

*hard · real sockets, real fsync, real kill -9*

Oracle for Chapter 5 · Hard — surviving a crash mid-write.

Two contracts, both new:

  RECOVERY IS TOTAL.  Opening a log whose tail is damaged must succeed and
  yield a valid prefix — every record up to the last complete, intact one, and
  nothing after it. Damage at the end of a log is normal; it is what a crash
  looks like. A store that refuses to open is a store you have lost.

  DEBRIS IS NOT DATA.  A partial record, a zero-filled tail, or a flipped byte
  must never be mistaken for something you wrote. Structure alone cannot tell
  them apart: on this format a run of zero bytes parses as a perfectly legal
  empty record.

  AND THE OLD ONE STILL HOLDS.  Anything acknowledged survives.

Every test here kills a *plausible wrong* recovery:
    - raising on a torn tail        -> the store cannot be opened at all
    - trusting structure alone      -> zeros become a key
    - recovering but not truncating -> the next append extends the garbage

## Segments

| file | what it forces | tests |
| --- | --- | --- |
| `test_1_a_record_that_can_prove_itself.py` | A record that can prove itself | 2 |
| `test_2_recover_to_a_valid_prefix.py` | Recover to a valid prefix | 4 |
| `test_3_acknowledged_means_durable.py` | Acknowledged means durable | 1 |
| `test_4_the_header_is_data_too.py` | The header is data too | 3 |

## Running it

```
pytest tests/ch5/test_1_a_record_that_can_prove_itself.py   # one segment
pytest tests/ch5                                            # the whole chapter
pytest                                                      # everything you have built so far
```
