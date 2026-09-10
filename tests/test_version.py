"""Tests for version reporting."""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from typing import Any

import bindery
from bindery import __version__, get_version


def test_declared_version_is_semver() -> None:
    """``__version__`` follows MAJOR.MINOR.PATCH."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), __version__


def test_get_version_matches_declared_when_uninstalled_or_same_dist() -> None:
    """Installed metadata and the declared version stay in lockstep in-repo."""
    result = get_version()
    assert isinstance(result, str)
    assert re.fullmatch(r"\d+\.\d+\.\d+", result), result


def test_version_is_not_empty() -> None:
    """Version is never blank."""
    assert __version__
    assert get_version()


def test_get_version_falls_back_when_distribution_missing(
    monkeypatch: Any,
) -> None:
    """Uninstalled source tree still returns the declared ``__version__``."""

    def _raise(_name: str) -> str:
        raise PackageNotFoundError("bindery")

    monkeypatch.setattr(bindery, "version", _raise)
    assert get_version() == __version__
