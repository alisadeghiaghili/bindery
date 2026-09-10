"""Smoke tests for package import and public surface."""

from __future__ import annotations

import bindery


def test_import_bindery() -> None:
    """Package imports without side effects."""
    assert bindery is not None


def test_public_exports_include_version_and_errors() -> None:
    """Public API for v0.1.0 is version helpers plus the exception tree."""
    expected = {
        "__version__",
        "get_version",
        "BinderyError",
        "BinderyConfigError",
        "BinderyIOError",
        "BinderyValidationError",
    }
    assert expected.issubset(set(bindery.__all__))


def test_all_exports_are_resolvable() -> None:
    """Every name in ``__all__`` exists on the package."""
    for name in bindery.__all__:
        assert hasattr(bindery, name), name
