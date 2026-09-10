"""Command-line entry point for bindery."""

from __future__ import annotations

import sys
from pathlib import Path

from bindery import get_version
from bindery.exceptions import BinderyError
from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.orchestration.pipeline import run_job
from bindery.orchestration.progress import ProgressEvent

__all__ = ["main"]

_USAGE = """\
Usage:
  bindery --version
  bindery --help
  bindery build SOURCE -o OUTPUT [options]

Assemble a folder of page images into a single PDF.

build options:
  -o, --output PATH     Output PDF path (required)
  --margin N            Uniform margin in pixels (default 0)
  --grayscale           Convert pages to grayscale
  --stamp               Stamp 1-based page numbers in the footer
  --dpi N               PDF page geometry dpi (default 300)
  --force               Rebuild even if output is up to date
"""


def _print_progress(event: ProgressEvent) -> None:
    """Render a single progress event on stderr.

    Args:
        event: Pipeline progress notification.

    Examples:
        >>> _print_progress(ProgressEvent(stage="done", completed=1, total=1))
    """
    if event.stage == "transform":
        label = event.current or ""
        print(
            f"[transform {event.completed}/{event.total}] {label}",
            file=sys.stderr,
            end="\r" if event.completed < event.total else "\n",
            flush=True,
        )
        return
    if event.stage == "discover":
        print(f"[discover] {event.message or ''}", file=sys.stderr)
        return
    if event.stage == "assemble":
        print(f"[assemble] {event.current or ''}", file=sys.stderr)
        return
    if event.stage == "skipped":
        print("[skip] output up to date", file=sys.stderr)
        return
    if event.stage == "done":
        print(f"[done] {event.message or ''}", file=sys.stderr)


def _cmd_build(args: list[str]) -> int:
    """Parse ``build`` arguments and run one job.

    Args:
        args: Arguments after the ``build`` verb.

    Returns:
        int: ``0`` on success, ``2`` on usage error, ``3`` on validation, ``4`` on I/O.
    """
    if not args:
        print("bindery: build requires a SOURCE directory", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2

    source = Path(args[0])
    output: Path | None = None
    margin = 0
    grayscale = False
    stamp = False
    dpi = 300
    force = False

    i = 1
    while i < len(args):
        token = args[i]
        if token in ("-o", "--output"):
            if i + 1 >= len(args):
                print("bindery: --output requires a path", file=sys.stderr)
                return 2
            output = Path(args[i + 1])
            i += 2
            continue
        if token == "--margin":
            if i + 1 >= len(args):
                print("bindery: --margin requires an integer", file=sys.stderr)
                return 2
            try:
                margin = int(args[i + 1])
            except ValueError:
                print(f"bindery: invalid --margin value: {args[i + 1]}", file=sys.stderr)
                return 2
            i += 2
            continue
        if token == "--dpi":
            if i + 1 >= len(args):
                print("bindery: --dpi requires an integer", file=sys.stderr)
                return 2
            try:
                dpi = int(args[i + 1])
            except ValueError:
                print(f"bindery: invalid --dpi value: {args[i + 1]}", file=sys.stderr)
                return 2
            i += 2
            continue
        if token == "--grayscale":
            grayscale = True
            i += 1
            continue
        if token == "--stamp":
            stamp = True
            i += 1
            continue
        if token == "--force":
            force = True
            i += 1
            continue
        print(f"bindery: unknown build option: {token}", file=sys.stderr)
        return 2

    if output is None:
        print("bindery: build requires -o/--output", file=sys.stderr)
        return 2

    try:
        config = JobConfig(
            source_dir=source,
            output_path=output,
            margins=MarginSpec.uniform(margin),
            grayscale=grayscale,
            stamp_page_numbers=stamp,
            dpi=dpi,
            force=force,
        )
        report = run_job(config, on_progress=_print_progress)
    except BinderyError as exc:
        print(f"bindery: {exc}", file=sys.stderr)
        name = type(exc).__name__
        if "Validation" in name or "Config" in name:
            return 3
        return 4

    if report.skipped:
        print(f"Up to date: {report.output_path} ({report.page_count} pages)")
    else:
        print(f"Wrote {report.output_path} ({report.page_count} pages)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the bindery CLI.

    Args:
        argv: Argument list without the program name. ``None`` uses
            ``sys.argv[1:]``.

    Returns:
        int: ``0`` success, ``2`` usage, ``3`` validation, ``4`` I/O.

    Examples:
        >>> main(["--version"])  # doctest: +SKIP
        bindery 0.4.0
        0
    """
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args in (["--version"], ["-V"]):
        print(f"bindery {get_version()}")
        return 0

    if args in (["--help"], ["-h"]):
        print(_USAGE)
        return 0

    if args[0] == "build":
        return _cmd_build(args[1:])

    print(f"bindery: unknown arguments: {' '.join(args)}", file=sys.stderr)
    print("Try: bindery --help", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
