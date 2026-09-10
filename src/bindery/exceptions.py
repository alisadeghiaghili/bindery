"""Exception hierarchy for :mod:`bindery`.

All public errors raised by bindery derive from :class:`BinderyError`.
Callers can catch the root type for any library failure, or a subclass
when they need to recover from a specific class of problem.
"""

from __future__ import annotations

__all__ = [
    "BinderyConfigError",
    "BinderyError",
    "BinderyIOError",
    "BinderyValidationError",
]


class BinderyError(Exception):
    """Base class for every error raised by bindery.

    Examples:
        >>> try:
        ...     raise BinderyError("something failed")
        ... except BinderyError as exc:
        ...     str(exc)
        'something failed'
    """


class BinderyConfigError(BinderyError):
    """Raised when configuration values are missing, conflicting, or invalid.

    Examples:
        >>> try:
        ...     raise BinderyConfigError("margin must be >= 0")
        ... except BinderyConfigError as exc:
        ...     str(exc)
        'margin must be >= 0'
    """


class BinderyIOError(BinderyError):
    """Raised when reading inputs or writing outputs fails.

    Examples:
        >>> try:
        ...     raise BinderyIOError("cannot read: pages/")
        ... except BinderyIOError as exc:
        ...     str(exc)
        'cannot read: pages/'
    """


class BinderyValidationError(BinderyError):
    """Raised when inputs fail domain validation before any I/O runs.

    Examples:
        >>> try:
        ...     raise BinderyValidationError("no page images found")
        ... except BinderyValidationError as exc:
        ...     str(exc)
        'no page images found'
    """
