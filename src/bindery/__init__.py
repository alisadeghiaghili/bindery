"""bindery — assemble image folders and PDF pages into a single PDF.

Public surface includes version metadata, the exception hierarchy, and the
assemble pipeline used by the CLI.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from bindery.exceptions import (
    BinderyConfigError,
    BinderyError,
    BinderyIOError,
    BinderyValidationError,
)

__all__ = [
    "BinderyConfigError",
    "BinderyError",
    "BinderyIOError",
    "BinderyValidationError",
    "__version__",
    "get_version",
]


def get_version() -> str:
    """Return the installed distribution version of bindery.

    Falls back to the declared package version when the distribution is not
    installed (editable source tree without a build).

    Returns:
        str: Version string in ``MAJOR.MINOR.PATCH`` form, for example ``"0.3.0"``.

    Examples:
        >>> get_version()  # doctest: +SKIP
        '0.3.0'
    """
    try:
        return version("bindery")
    except PackageNotFoundError:
        return __version__


#: Declared package version used when metadata is unavailable.
__version__: str = "0.3.0"
