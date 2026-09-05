"""Course structure: chapters, beats, and how to run one of them.

A **chapter** is one video. A **beat** is one segment inside it: a handful of
tests that go red together, get implemented together, and go green together.
Beats are declared at the top of each `test_chNN_*.py` as `BEATS`, so the
chapter file stays the single readable spec for the chapter.

    pytest --outline        the whole course, chapter by chapter, with counts
    pytest --beat 3.2       one beat
    pytest --beat 3         one whole chapter
    pytest --upto 3.2       every beat from 1.1 through 3.2

`--upto` is the ratchet. A beat going green proves the new thing works;
`--upto` proves it did not cost you anything you had already built.
"""
import pytest


def _key(beat_id):
    return tuple(int(part) for part in beat_id.split("."))


def _beats_of(module):
    return getattr(module, "BEATS", None) or {}


def _beat_of(item):
    """The beat id an item belongs to, or None if it is outside the course."""
    module = getattr(item, "module", None)
    beats = _beats_of(module)
    if not beats:
        return None
    name = getattr(item, "originalname", None) or item.name.split("[")[0]
    for beat_id, (_title, names) in beats.items():
        if name in names:
            return beat_id
    return None


def pytest_addoption(parser):
    group = parser.getgroup("course", "hardmode course structure")
    group.addoption(
        "--beat", action="store", default=None, metavar="ID",
        help="run one beat (--beat 3.2) or one whole chapter (--beat 3)",
    )
    group.addoption(
        "--upto", action="store", default=None, metavar="ID",
        help="run every beat from 1.1 through ID, inclusive (the ratchet)",
    )
    group.addoption(
        "--outline", action="store_true", default=False,
        help="print the course outline and stop",
    )


def _write_outline(config, items):
    out = config.pluginmanager.get_plugin("terminalreporter")
    if out is None:
        return

    counts = {}
    for item in items:
        beat_id = _beat_of(item)
        if beat_id:
            counts[beat_id] = counts.get(beat_id, 0) + 1

    chapters = {}
    for item in items:
        module = getattr(item, "module", None)
        beats = _beats_of(module)
        if not beats:
            continue
        chapter = next(iter(beats)).split(".")[0]
        chapters[chapter] = module

    out.write_line("")
    out.write_line("hardmode · distributed consensus", bold=True)
    out.write_line("")

    total = 0
    for chapter in sorted(chapters, key=int):
        module = chapters[chapter]
        title = getattr(module, "TITLE", module.__name__)
        tier = getattr(module, "TIER", "")
        out.write_line(f"  ch {chapter:>2}  {title}", bold=True)
        out.write_line(f"        {tier}")
        for beat_id, (beat_title, _names) in _beats_of(module).items():
            n = counts.get(beat_id, 0)
            total += n
            unit = "test " if n == 1 else "tests"
            out.write_line(f"        {beat_id:<6} {beat_title:<48} {n:>3} {unit}")
        out.write_line("")

    out.write_line(f"  {total} tests across {len(counts)} beats "
                   f"in {len(chapters)} chapters")
    out.write_line("")
    out.write_line("  pytest --beat 3.2      one segment")
    out.write_line("  pytest --upto 3.2      that segment and everything before it")
    out.write_line("")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--outline"):
        _write_outline(config, items)
        config.hook.pytest_deselected(items=list(items))
        items[:] = []
        return

    beat = config.getoption("--beat")
    upto = config.getoption("--upto")
    if beat and upto:
        raise pytest.UsageError("use --beat or --upto, not both")
    if not beat and not upto:
        return

    selector = beat or upto
    try:
        wanted = _key(selector)
    except ValueError:
        raise pytest.UsageError(
            f"{selector!r} is not a beat id; expected 3 or 3.2"
        ) from None

    keep, drop = [], []
    for item in items:
        beat_id = _beat_of(item)
        if beat_id is None:
            drop.append(item)
            continue
        found = _key(beat_id)
        if beat:
            hit = found[: len(wanted)] == wanted
        else:
            hit = found[: len(wanted)] <= wanted
        (keep if hit else drop).append(item)

    if not keep:
        raise pytest.UsageError(
            f"no tests for {selector!r}; run `pytest --outline` for the course map"
        )

    if drop:
        config.hook.pytest_deselected(items=drop)
    items[:] = keep


def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--outline"):
        session.exitstatus = 0
