"""Fixtures for chapter 1."""

import pytest


@pytest.fixture


def path(tmp_path):
    return str(tmp_path / "test.log")
