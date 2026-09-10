"""Tests for the exception hierarchy."""

from __future__ import annotations

import pytest

from bindery.exceptions import (
    BinderyConfigError,
    BinderyError,
    BinderyIOError,
    BinderyValidationError,
)


@pytest.mark.parametrize(
    "exc_type",
    [
        BinderyConfigError,
        BinderyIOError,
        BinderyValidationError,
    ],
)
def test_subclasses_are_bindery_errors(exc_type: type[BinderyError]) -> None:
    """Every public error type inherits from :class:`BinderyError`."""
    exc = exc_type("boom")
    assert isinstance(exc, BinderyError)
    assert isinstance(exc, Exception)
    assert str(exc) == "boom"


def test_base_error_is_catchable_as_exception() -> None:
    """Root type is a normal :class:`Exception` subclass."""
    assert issubclass(BinderyError, Exception)


def test_hierarchy_is_distinct() -> None:
    """Sibling error types are not subclasses of each other."""
    assert not issubclass(BinderyConfigError, BinderyIOError)
    assert not issubclass(BinderyIOError, BinderyValidationError)
    assert not issubclass(BinderyValidationError, BinderyConfigError)
