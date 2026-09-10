"""Command-line entry point for bindery.

v0.1.0 exposes only version reporting. The ``build`` / ``inspect`` /
``doctor`` commands ship in later stages.
"""

from __future__ import annotations

import sys

from bindery import get_version

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Run the bindery CLI.

    Args:
        argv: Argument list without the program name. ``None`` uses
            ``sys.argv[1:]``. Unknown arguments are rejected with exit code
            ``2`` in this release.

    Returns:
        int: Process exit code. ``0`` on success, ``2`` on usage error.

    Examples:
        >>> main(["--version"])
        bindery 0.1.0
        0
    """
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args in (["--version"], ["-V"]):
        print(f"bindery {get_version()}")
        return 0

    if args in (["--help"], ["-h"]):
        print("Usage: bindery [--version]")
        print("Assemble image folders into PDF. Full commands land in v0.5.0.")
        return 0

    print(f"bindery: unknown arguments: {' '.join(args)}", file=sys.stderr)
    print("Try: bindery --help", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
