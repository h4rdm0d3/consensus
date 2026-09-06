# hardmode · consensus

Goal: Build Raft consensus algorithm by building through testable scenarios.
Stack: Python, Rust

To develop a sense of progression, we will start small. A rough map of what we will build:

- A persistent log
- Key value store
- Replicating the key-value state across machines.

Raft's purpose is to ensure replication across machines is consistent.

## Start

```sh
uv sync --extra dev
pytest -q          # red until you implement the stubs
```

Chapter 1 begins in `consensus/logfile.py`. Read the docstring, then open
`fixtures/mystery.log` and recover the three records it holds. Do that by hand
before writing code.

To start at a later chapter, check out its starting point. The chapters before
it are implemented, this one is red, and nothing from the chapters after it is
in the tree:

```sh
git checkout start/ch3
pytest             # chapter 3 red, chapters 1 and 2 green
```
