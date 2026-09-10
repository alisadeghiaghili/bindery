"""Validation edge cases."""

from __future__ import annotations

import pytest

from bindery.domain.validate import ensure_positive_size
from bindery.exceptions import BinderyValidationError


def test_ensure_positive_size_rejects_bool() -> None:
    """Booleans are not valid dimensions."""
    with pytest.raises(BinderyValidationError, match="must be an int"):
        ensure_positive_size((True, 1), context="image")


def test_ensure_positive_size_rejects_float() -> None:
    """Floats are rejected even if whole."""
    with pytest.raises(BinderyValidationError, match="must be an int"):
        ensure_positive_size((1.0, 1), context="image")  # type: ignore[arg-type]


def test_ensure_positive_size_context_in_message() -> None:
    """Context label appears in the error."""
    with pytest.raises(BinderyValidationError, match="thumb"):
        ensure_positive_size((0, 1), context="thumb")
