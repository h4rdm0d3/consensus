"""The outline is a partition of the tests, and this is what keeps it one.

Every chapter file declares BEATS at the top. That outline drives `--beat`,
`--upto`, and the video's chapter markers, so it has to stay honest as tests
get added and renamed. Three failures are possible and all three are silent
without this file:

    a test in no beat        -> it never runs under --beat or --upto
    a beat naming no test    -> a segment you would record against nothing
    an import the stub lacks -> chapter N breaks collection for 1..N-1 too

The third is the one that bites on the stubs branch. A reader starting
chapter 1 collects every chapter's oracle, so a later chapter importing a
name `consensus/` does not define yet takes down the whole run, including
`--outline`. Every name an oracle imports must exist as a stub from the
first day of the course.

This file never imports a chapter module in order to answer the third
question -- it reads the source -- so it still reports when the others cannot
run at all.
"""
import ast
import importlib
from pathlib import Path

import pytest

TESTS = Path(__file__).parent


def chapter_paths():
    return sorted(TESTS.glob("test_ch*.py"))


def _import(path):
    try:
        return importlib.import_module(path.stem), None
    except Exception as exc:  # noqa: BLE001 -- reported as a test failure
        return None, exc


def chapter_modules():
    out = []
    for path in chapter_paths():
        mod, _exc = _import(path)
        if mod is not None and hasattr(mod, "BEATS"):
            out.append(mod)
    return out


IMPORTABLE = chapter_modules()


def test_there_are_chapters_to_run():
    assert chapter_paths(), "no chapter files found"


@pytest.mark.parametrize("path", chapter_paths(), ids=lambda p: p.stem)
def test_every_name_an_oracle_imports_exists(path):
    """Read the source, so this still answers when the import would fail."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if not node.module or not node.module.startswith("consensus"):
            continue
        module = importlib.import_module(node.module)
        for alias in node.names:
            assert hasattr(module, alias.name), (
                f"{path.name} imports {alias.name!r} from {node.module}, which "
                f"does not define it. On the stubs branch that is a collection "
                f"error, and a collection error in one chapter takes down every "
                f"other chapter with it -- including `pytest --outline`. Declare "
                f"{alias.name!r} as a stub."
            )


@pytest.mark.parametrize("path", chapter_paths(), ids=lambda p: p.stem)
def test_every_chapter_module_imports(path):
    mod, exc = _import(path)
    assert mod is not None, f"{path.name} does not import: {exc!r}"
    assert hasattr(mod, "BEATS"), f"{path.name} declares no BEATS"


@pytest.mark.parametrize("mod", IMPORTABLE, ids=lambda m: m.__name__)
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


@pytest.mark.parametrize("mod", IMPORTABLE, ids=lambda m: m.__name__)
def test_every_beat_names_real_tests(mod):
    defined = {n for n in vars(mod) if n.startswith("test_")}
    for beat_id, (title, names) in mod.BEATS.items():
        assert names, f"{mod.__name__} {beat_id} ({title}) is empty"
        ghosts = sorted(set(names) - defined)
        assert not ghosts, (
            f"{mod.__name__} {beat_id} ({title}) names tests that do not "
            f"exist: {ghosts}"
        )


@pytest.mark.parametrize("mod", IMPORTABLE, ids=lambda m: m.__name__)
def test_beat_ids_are_ordered_and_share_one_chapter(mod):
    ids = list(mod.BEATS)
    keys = [tuple(int(p) for p in i.split(".")) for i in ids]

    assert all(len(k) == 2 for k in keys), f"{mod.__name__}: beat ids are CH.N"
    chapters = {k[0] for k in keys}
    assert len(chapters) == 1, (
        f"{mod.__name__} declares beats from several chapters: {chapters}"
    )
    assert keys == sorted(keys), (
        f"{mod.__name__}: beats are out of order -- they are the running order "
        f"of the video, so declare them in it: {ids}"
    )
    assert [k[1] for k in keys] == list(range(1, len(keys) + 1)), (
        f"{mod.__name__}: beat numbers have a gap: {ids}"
    )


@pytest.mark.parametrize("mod", IMPORTABLE, ids=lambda m: m.__name__)
def test_every_chapter_is_labelled(mod):
    assert getattr(mod, "TITLE", None), f"{mod.__name__} has no TITLE"
    assert getattr(mod, "TIER", None), f"{mod.__name__} has no TIER"
