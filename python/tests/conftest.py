"""Shared by every chapter.

pytest loads this file automatically and makes the fixtures below available to
every test underneath it, with no import. Only things that are true for the
whole course belong here. A chapter's own instruments stay in that chapter's
directory, because this file is present from chapter 1 onward and anything in
it is visible on day one.
"""

import pytest


@pytest.fixture


def path(tmp_path):
    """A path to a log file that does not exist yet, unique per test."""

    return str(tmp_path / "store.log")
