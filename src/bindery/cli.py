"""Command-line entry point for bindery."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from bindery import get_version
from bindery.adapters.fs import discover_page_files
from bindery.adapters.images import load_image
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
  bindery inspect SOURCE
  bindery doctor
  bindery gui

Assemble a folder of page images into a single PDF.

build options:
  -o, --output PATH     Output PDF path (required)
  --margin N            Uniform margin in pixels (default 0)
  --grayscale           Convert pages to grayscale
  --stamp               Stamp 1-based page numbers in the footer
  --dpi N               PDF page geometry dpi (default 300)
  --title TEXT          PDF document title (default: output file stem)
  --author TEXT         PDF document author metadata
  --force               Rebuild even if output is up to date

inspect:
  List pages in assemble order with pixel sizes.

doctor:
  Report Python, bindery, and dependency health.

gui:
  Launch the desktop GUI (tkinter).
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


def _cmd_inspect(args: list[str]) -> int:
    """Run ``bindery inspect``.

    Args:
        args: Arguments after ``inspect``. Expects a single SOURCE path.

    Returns:
        int: ``0`` ok, ``2`` usage, ``3`` validation, ``4`` I/O.
    """
    if not args:
        print("bindery: inspect requires a SOURCE directory", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2

    source = Path(args[0])
    try:
        pages = discover_page_files(source)
    except BinderyError as exc:
        print(f"bindery: {exc}", file=sys.stderr)
        name = type(exc).__name__
        return 3 if "Validation" in name or "Config" in name else 4

    print(f"source: {source}")
    print(f"pages:  {len(pages)}")
    print("order:")
    for page in pages:
        try:
            image = load_image(page.path)
            try:
                width, height = image.size
            finally:
                image.close()
            size_label = f"{width}x{height}"
        except BinderyError:
            size_label = "unreadable"
        print(f"  {page.index + 1:4d}. {page.name:30s} {size_label}")
    return 0


def _safe_platform() -> str:
    """Return a platform label that cannot crash on Windows WMI probes.

    ``platform.platform()`` may raise fatal WinError/OOM from WMI on some
    hosts; doctor reports ``sys.platform`` instead.

    Returns:
        str: ``sys.platform`` value, e.g. ``"win32"``.

    Examples:
        >>> isinstance(_safe_platform(), str)
        True
    """
    return sys.platform


def _cmd_doctor() -> int:
    """Run ``bindery doctor`` environment checks.

    Returns:
        int: Always ``0``. Prints a health report; host probe failures are
            reported inline rather than aborting the command.
    """
    import platform

    lines: list[str] = []
    lines.append(f"bindery:  {get_version()}")
    lines.append(f"python:   {platform.python_version()} ({sys.executable})")
    lines.append(f"platform: {_safe_platform()}")

    for module_name in ("PIL", "img2pdf", "pypdf"):
        try:
            module = __import__(module_name)
        except ImportError:
            lines.append(f"{module_name}:  MISSING")
            continue
        version = getattr(module, "__version__", None) or getattr(module, "VERSION", None)
        label = "pillow" if module_name == "PIL" else module_name
        lines.append(f"{label}:  {version or 'unknown'}")

    try:
        import img2pdf

        has_convert = callable(getattr(img2pdf, "convert", None))
        lines.append(f"img2pdf API: {'ok' if has_convert else 'FAILED'}")
    except ImportError:
        lines.append("img2pdf API: FAILED")

    try:
        from pypdf import PdfReader, PdfWriter

        _ = (PdfReader, PdfWriter)
        lines.append("pypdf API:   ok")
    except ImportError:
        lines.append("pypdf API:   FAILED")

    for line in lines:
        print(line)
    return 0


def _int_or_cli_error(flag: str) -> Callable[[str], int]:
    """Build an argparse type that rejects non-integers with bindery wording.

    Args:
        flag: CLI flag name used in the error message (e.g. ``--margin``).

    Returns:
        Callable[[str], int]: Converter suitable for ``argparse`` ``type=``.

    Examples:
        >>> fn = _int_or_cli_error("--margin")
        >>> fn("3")
        3
    """

    def _parse(value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid {flag} value: {value}") from None

    return _parse


class _BuildArgumentParser(argparse.ArgumentParser):
    """Argument parser that prints bindery usage errors and exits ``2``."""

    def error(self, message: str) -> NoReturn:
        """Print a usage error on stderr and exit with code ``2``.

        Args:
            message: argparse error text; unrecognized flags are reworded.

        Examples:
            >>> isinstance(_BuildArgumentParser(prog="bindery"), argparse.ArgumentParser)
            True
        """
        lower = message.lower()
        if "unrecognized arguments" in lower:
            unknown = message.split(":", 1)[-1].strip()
            message = f"unknown build option: {unknown}"
        elif "invalid int value" in lower:
            message = message.replace("invalid int value", "invalid value")
        print(f"bindery: {message}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        raise SystemExit(2)


def _build_arg_parser() -> _BuildArgumentParser:
    """Create the argparse parser for ``bindery build``.

    Returns:
        _BuildArgumentParser: Parser configured for the build verb.

    Examples:
        >>> _build_arg_parser().prog
        'bindery-build'
    """
    parser = _BuildArgumentParser(
        prog="bindery-build",
        add_help=False,
        description="Assemble a folder of page images into a single PDF.",
    )
    parser.add_argument("source", type=Path, help="Directory containing page images")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output PDF path")
    parser.add_argument(
        "--margin",
        type=_int_or_cli_error("--margin"),
        default=0,
        help="Uniform margin in pixels (default 0)",
    )
    parser.add_argument("--grayscale", action="store_true", help="Convert pages to grayscale")
    parser.add_argument("--stamp", action="store_true", help="Stamp 1-based page numbers")
    parser.add_argument(
        "--dpi",
        type=_int_or_cli_error("--dpi"),
        default=300,
        help="PDF page geometry dpi (default 300)",
    )
    parser.add_argument("--title", type=str, default=None, help="PDF document title")
    parser.add_argument("--author", type=str, default=None, help="PDF document author")
    parser.add_argument("--force", action="store_true", help="Rebuild even if up to date")
    return parser


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

    parser = _build_arg_parser()
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2

    try:
        config = JobConfig(
            source_dir=ns.source,
            output_path=ns.output,
            margins=MarginSpec.uniform(ns.margin),
            grayscale=ns.grayscale,
            stamp_page_numbers=ns.stamp,
            dpi=ns.dpi,
            force=ns.force,
            title=ns.title,
            author=ns.author,
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
        bindery 0.7.0
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

    if args[0] == "inspect":
        return _cmd_inspect(args[1:])

    if args[0] == "doctor":
        return _cmd_doctor()

    if args[0] == "gui":
        if len(args) > 1 and args[1] in ("--help", "-h"):
            print(_USAGE)
            return 0
        from bindery.gui import main as gui_main

        return gui_main([])

    print(f"bindery: unknown arguments: {' '.join(args)}", file=sys.stderr)
    print("Try: bindery --help", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
