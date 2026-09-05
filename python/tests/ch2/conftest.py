"""Fixtures for chapter 2."""

import pytest


@pytest.fixture


def path(tmp_path):
    return str(tmp_path / "store.log")
