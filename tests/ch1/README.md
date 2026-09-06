# Chapter 1: The file won't read back

*easy · single process, seeded faults, everything reproducible*

Oracle for Chapter 1 · Easy: record framing on disk.

`fixtures/mystery.log` came from a store that appended every write to a file.
It holds three records. Recover them by hand before you write any code, and
write down what you find.

Contract:
    LogFile(path).append(key, value)     appends one record, never rewrites
    LogFile(path).scan()  -> Iterator[(key, value)] in write order

Every test here kills a *plausible wrong* format, not just an empty one:

```
- key+value concatenated        -> roundtrip garbage (the mystery.log bug)
- a delimiter byte (, : \n \0)  -> dies when the payload contains it
- a character-count length      -> dies on multibyte (chars != bytes)
- rewriting the file each time  -> dies on the append-only check
```

## Segments

| file | what it forces | tests |
| --- | --- | --- |
| `test_1_record_reads_back.py` | Record reads back | 3 |
| `test_2_payloads_that_break_your_framing.py` | Payloads that break your framing | 4 |
| `test_3_log_only_grows.py` | The log only grows | 3 |
| `test_4_scan_does_not_load_file.py` | scan() does not load the file | 1 |
| `test_5_format_you_did_not_write.py` | A format you did not write | 1 |

## Running it

```
pytest tests/ch1/test_1_record_reads_back.py   # one segment
pytest tests/ch1                               # the whole chapter
pytest                                         # everything you have built so far
```
