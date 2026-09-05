"""The outline is a partition of the tests, and this is what keeps it one.

Every chapter file declares BEATS at the top. That outline drives `--beat`,
`--upto`, and the video's chapter markers, so it has to stay honest as tests
get added and renamed. Two failures are possible and both are silent without
this file:

    a test in no beat        -> it never runs under --beat or --upto
    a beat naming no test    -> a segment you would record against nothing

Which is the same shape as the framing bug in chapter 1: a mapping is only
trustworthy when it is total and injective.
"""
import importlib
import pkgutil
from pathlib import Path

import pytest

TESTS = Path(__file__).parent


def chapter_modules():
    mods = []
    for info in pkgutil.iter_modules([str(TESTS)]):
        if not info.name.startswith("test_ch"):
            continue
        mod = importlib.import_module(info.name)
        if hasattr(mod, "BEATS"):
            mods.append(mod)
    return sorted(mods, key=lambda m: m.__name__)


def test_there_are_chapters_to_run():
    assert chapter_modules(), "no chapter declared BEATS — --beat selects nothing"


@pytest.mark.parametrize("mod", chapter_modules(), ids=lambda m: m.__name__)
def test_every_test_belongs_to_exactly_one_beat(mod):
    defined = {n for n in vars(mod) if n.startswith("test_")}
    seen = {}
    for beat_id, (_title, names) in mod.BEATS.items():
        for name in names:
            seen.setdefault(name, []).append(beat_id)

    missing = sorted(defined - set(seen))
    assert not missing, (
        f"{mod.__name__}: {missing} are in no beat, so they never run under "
        "--beat or --upto. Add them to BEATS."
    )

    twice = {n: b for n, b in seen.items() if len(b) > 1}
    assert not twice, f"{mod.__name__}: listed in more than one beat: {twice}"


@pytest.mark.parametrize("mod", chapter_modules(), ids=lambda m: m.__name__)
def test_every_beat_names_real_tests(mod):
    defined = {n for n in vars(mod) if n.startswith("test_")}
    for beat_id, (title, names) in mod.BEATS.items():
        assert names, f"{mod.__name__} {beat_id} ({title}) is empty"
        ghosts = sorted(set(names) - defined)
        assert not ghosts, (
            f"{mod.__name__} {beat_id} ({title}) names tests that do not "
            f"exist: {ghosts}"
        )


@pytest.mark.parametrize("mod", chapter_modules(), ids=lambda m: m.__name__)
def test_beat_ids_are_ordered_and_share_one_chapter(mod):
    ids = list(mod.BEATS)
    keys = [tuple(int(p) for p in i.split(".")) for i in ids]

    assert all(len(k) == 2 for k in keys), f"{mod.__name__}: beat ids are CH.N"
    chapters = {k[0] for k in keys}
    assert len(chapters) == 1, (
        f"{mod.__name__} declares beats from several chapters: {chapters}"
    )
    assert keys == sorted(keys), (
        f"{mod.__name__}: beats are out of order — they are the running order "
        f"of the video, so declare them in it: {ids}"
    )
    assert [k[1] for k in keys] == list(range(1, len(keys) + 1)), (
        f"{mod.__name__}: beat numbers have a gap: {ids}"
    )


@pytest.mark.parametrize("mod", chapter_modules(), ids=lambda m: m.__name__)
def test_every_chapter_is_labelled(mod):
    assert getattr(mod, "TITLE", None), f"{mod.__name__} has no TITLE"
    assert getattr(mod, "TIER", None), f"{mod.__name__} has no TIER"
