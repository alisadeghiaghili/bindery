"""Smoke tests for package import and public surface."""

from __future__ import annotations

import bindery


def test_import_bindery() -> None:
    """Package imports without side effects."""
    assert bindery is not None


def test_public_exports_include_version_errors_and_pipeline() -> None:
    """Public API includes version helpers, errors, and the job pipeline."""
    expected = {
        "__version__",
        "get_version",
        "BinderyError",
        "BinderyConfigError",
        "BinderyIOError",
        "BinderyValidationError",
        "JobConfig",
        "JobReport",
        "run_job",
    }
    assert expected.issubset(set(bindery.__all__))


def test_all_exports_are_resolvable() -> None:
    """Every name in ``__all__`` exists on the package."""
    for name in bindery.__all__:
        assert hasattr(bindery, name), name
