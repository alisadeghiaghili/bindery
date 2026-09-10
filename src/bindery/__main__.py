"""Allow ``python -m bindery``."""

from __future__ import annotations

from bindery.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
