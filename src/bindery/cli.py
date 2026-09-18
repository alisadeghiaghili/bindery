"""Command-line entry point for bindery."""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

from bindery import get_version
from bindery.adapters.fs import discover_page_files
from bindery.adapters.images import load_image
from bindery.exceptions import BinderyError, BinderyValidationError
from bindery.models.config import JobConfig
from bindery.models.crop import CropBox, MarginSpec
from bindery.models.job_config_file import job_config_from_file
from bindery.models.page import PageFile
from bindery.models.page_size import parse_page_size
from bindery.orchestration.pipeline import run_job, select_pages, transform_page
from bindery.orchestration.progress import ProgressEvent

__all__ = ["main"]

_USAGE = """\
Usage:
  bindery --version
  bindery --help
  bindery build SOURCE -o OUTPUT [options]
  bindery preview SOURCE -o IMAGE [options]
  bindery job JOBFILE [--dry-run]
  bindery inspect SOURCE
  bindery doctor
  bindery gui

Assemble a folder of page images into a single PDF.

build / preview options:
  -o, --output PATH     Output path (required)
  --margin N            Uniform margin in pixels (default 0)
  --grayscale           Convert pages to grayscale
  --stamp               Stamp 1-based page numbers in the footer
  --dpi N               PDF page geometry dpi (default 300)
  --title TEXT          PDF document title (build; default: output stem)
  --author TEXT         PDF document author metadata (build)
  --crop L,T,R,B        Crop box in source pixels (exclusive right/bottom)
  --rotate DEG          Clockwise rotate: 0, 90, 180, or 270
  --page-size SPEC      a4 | letter | WIDTHxHEIGHT (PDF points)
  --compress MODE       lossless (default) | jpeg
  --jpeg-quality N      JPEG quality 1-95 (default 85; jpeg only)
  --pages N1,N2,...     Explicit page file names in assemble order
  --exclude N1,N2,...   Drop these file names after discovery
  --extra-source DIR    Additional source directory (repeatable)
  --bookmarks MODE      none | filenames | chapters (default none)
  --page N              Preview only: 1-based page index (default 1)
  --force               Rebuild even if output is up to date (build)

job:
  Run a .toml/.json job file (multi-source chapters supported).
  --dry-run lists planned pages/options without writing a PDF.

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

    parser = _inspect_arg_parser()
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2

    source = ns.source
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


def _parse_crop(value: str) -> CropBox:
    """Parse ``L,T,R,B`` into a :class:`CropBox`.

    Args:
        value: Comma-separated integers.

    Returns:
        CropBox: Crop rectangle.

    Raises:
        argparse.ArgumentTypeError: If the token is not four integers.

    Examples:
        >>> _parse_crop("0,0,4,5").width
        4
    """
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"invalid --crop value: {value} (need L,T,R,B)")
    try:
        left, top, right, bottom = (int(part.strip()) for part in parts)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid --crop value: {value}") from None
    return CropBox(left=left, top=top, right=right, bottom=bottom)


def _parse_name_list(value: str) -> tuple[str, ...]:
    """Parse a comma-separated list of page file names.

    Args:
        value: ``"a.png,b.png"``.

    Returns:
        tuple[str, ...]: Non-empty names in order.

    Raises:
        argparse.ArgumentTypeError: If the list is empty.

    Examples:
        >>> _parse_name_list("a.png,b.png")
        ('a.png', 'b.png')
    """
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    if not names:
        raise argparse.ArgumentTypeError(f"invalid page list: {value!r}")
    return names


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


class _InspectArgumentParser(argparse.ArgumentParser):
    """Argument parser for ``bindery inspect`` with bindery usage wording."""

    def error(self, message: str) -> NoReturn:
        """Print a usage error on stderr and exit with code ``2``.

        Args:
            message: argparse error text.

        Examples:
            >>> isinstance(_InspectArgumentParser(prog="bindery-inspect"), argparse.ArgumentParser)
            True
        """
        if "the following arguments are required" in message.lower():
            message = "inspect requires a SOURCE directory"
        print(f"bindery: {message}", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        raise SystemExit(2)


def _add_transform_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach shared transform flags to a build/preview parser.

    Args:
        parser: Target parser.

    Examples:
        >>> callable(_add_transform_arguments)
        True
    """
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output path")
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
    parser.add_argument("--crop", type=_parse_crop, default=None, help="Crop L,T,R,B pixels")
    parser.add_argument(
        "--rotate",
        type=_int_or_cli_error("--rotate"),
        default=0,
        help="Clockwise rotate 0/90/180/270",
    )
    parser.add_argument("--page-size", default=None, help="a4 | letter | WIDTHxHEIGHT pt")
    parser.add_argument(
        "--compress",
        choices=("lossless", "jpeg"),
        default="lossless",
        help="lossless (default) or jpeg",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=_int_or_cli_error("--jpeg-quality"),
        default=85,
        help="JPEG quality 1-95 (jpeg only)",
    )
    parser.add_argument("--pages", type=_parse_name_list, default=None, help="Explicit page order")
    parser.add_argument(
        "--exclude",
        type=_parse_name_list,
        default=None,
        help="Page names to drop after discovery",
    )
    parser.add_argument(
        "--extra-source",
        action="append",
        default=None,
        dest="extra_sources",
        help="Additional source directory (repeatable)",
    )
    parser.add_argument(
        "--bookmarks",
        choices=("none", "filenames", "chapters"),
        default="none",
        help="PDF outline mode",
    )


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
    _add_transform_arguments(parser)
    parser.add_argument("--title", type=str, default=None, help="PDF document title")
    parser.add_argument("--author", type=str, default=None, help="PDF document author")
    parser.add_argument("--force", action="store_true", help="Rebuild even if up to date")
    return parser


def _preview_arg_parser() -> _BuildArgumentParser:
    """Create the argparse parser for ``bindery preview``.

    Returns:
        _BuildArgumentParser: Parser configured for the preview verb.

    Examples:
        >>> _preview_arg_parser().prog
        'bindery-preview'
    """
    parser = _BuildArgumentParser(
        prog="bindery-preview",
        add_help=False,
        description="Write one transformed page image for inspection.",
    )
    parser.add_argument("source", type=Path, help="Directory containing page images")
    _add_transform_arguments(parser)
    parser.add_argument(
        "--page",
        type=_int_or_cli_error("--page"),
        default=1,
        help="1-based page index to preview (default 1)",
    )
    return parser


def _inspect_arg_parser() -> _InspectArgumentParser:
    """Create the argparse parser for ``bindery inspect``.

    Returns:
        _InspectArgumentParser: Parser configured for the inspect verb.

    Examples:
        >>> _inspect_arg_parser().prog
        'bindery-inspect'
    """
    parser = _InspectArgumentParser(
        prog="bindery-inspect",
        add_help=False,
        description="List pages in assemble order with pixel sizes.",
    )
    parser.add_argument("source", type=Path, help="Directory containing page images")
    return parser


def _resolve_page_names(
    discovered: list[PageFile],
    pages: tuple[str, ...] | None,
    exclude: tuple[str, ...] | None,
) -> tuple[str, ...] | None:
    """Compute explicit page order from --pages/--exclude.

    Args:
        discovered: Naturally sorted pages from the source directory.
        pages: Optional explicit order.
        exclude: Optional names to drop.

    Returns:
        tuple[str, ...] | None: Explicit order, or ``None`` for natural sort.

    Raises:
        BinderyValidationError: If exclude references a missing name.

    Examples:
        >>> callable(_resolve_page_names)
        True
    """
    if pages is not None:
        return pages
    if exclude is None:
        return None
    exclude_set = set(exclude)
    available = {page.name for page in discovered}
    missing = exclude_set - available
    if missing:
        raise BinderyValidationError(f"exclude names not in source: {sorted(missing)}")
    return tuple(page.name for page in discovered if page.name not in exclude_set)


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
        if ns.page_size is not None:
            parse_page_size(ns.page_size)
        page_names = ns.pages
        extra = tuple(Path(p) for p in (ns.extra_sources or ()))
        exclude_names = ns.exclude
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
            crop=ns.crop,
            rotate=ns.rotate,
            page_size=ns.page_size,
            compress=ns.compress,
            jpeg_quality=ns.jpeg_quality,
            page_names=page_names,
            exclude_names=exclude_names,
            extra_sources=extra,
            bookmark_mode=ns.bookmarks,
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


def _cmd_preview(args: list[str]) -> int:
    """Run ``bindery preview`` and write one transformed page image.

    Args:
        args: Arguments after the ``preview`` verb.

    Returns:
        int: ``0`` on success, ``2`` usage, ``3`` validation, ``4`` I/O.
    """
    if not args:
        print("bindery: preview requires a SOURCE directory", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2

    parser = _preview_arg_parser()
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2

    try:
        if ns.page_size is not None:
            parse_page_size(ns.page_size)
        discovered = discover_page_files(ns.source)
        page_names = _resolve_page_names(discovered, ns.pages, ns.exclude)
        selected = select_pages(discovered, page_names)
        if not selected:
            print("bindery: no page images in source", file=sys.stderr)
            return 3
        if ns.page < 1 or ns.page > len(selected):
            print(
                f"bindery: --page must be 1..{len(selected)}, got {ns.page}",
                file=sys.stderr,
            )
            return 3
        page = selected[ns.page - 1]
        config = JobConfig(
            source_dir=ns.source,
            output_path=ns.output,
            margins=MarginSpec.uniform(ns.margin),
            grayscale=ns.grayscale,
            stamp_page_numbers=ns.stamp,
            dpi=ns.dpi,
            crop=ns.crop,
            rotate=ns.rotate,
            page_size=ns.page_size,
            compress=ns.compress,
            jpeg_quality=ns.jpeg_quality,
            page_names=page_names,
        )
        work_dir = Path(tempfile.mkdtemp(prefix="bindery-preview-"))
        try:
            written = transform_page(PageFile(path=page.path, index=page.index), config, work_dir)
            dest = Path(ns.output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            final = dest.with_suffix(written.suffix)
            final.write_bytes(written.read_bytes())
        finally:
            import shutil

            shutil.rmtree(work_dir, ignore_errors=True)
    except BinderyError as exc:
        print(f"bindery: {exc}", file=sys.stderr)
        name = type(exc).__name__
        if "Validation" in name or "Config" in name:
            return 3
        return 4

    print(f"Wrote preview {final} ({page.name})")
    return 0


def _cmd_job(args: list[str]) -> int:
    """Run ``bindery job`` from a job file.

    Args:
        args: Arguments after ``job``. Expects JOBFILE and optional ``--dry-run``.

    Returns:
        int: ``0`` success, ``2`` usage, ``3`` validation, ``4`` I/O.
    """
    if not args:
        print("bindery: job requires a JOBFILE path", file=sys.stderr)
        print(_USAGE, file=sys.stderr)
        return 2
    dry_run = False
    job_path: Path | None = None
    for token in args:
        if token == "--dry-run":
            dry_run = True
            continue
        if token.startswith("-"):
            print(f"bindery: unknown job option: {token}", file=sys.stderr)
            return 2
        if job_path is not None:
            print("bindery: job accepts a single JOBFILE", file=sys.stderr)
            return 2
        job_path = Path(token)
    if job_path is None:
        print("bindery: job requires a JOBFILE path", file=sys.stderr)
        return 2

    try:
        config = job_config_from_file(job_path)
        if dry_run:
            from bindery.orchestration.pipeline import discover_job_pages

            pages, chapter_starts, chapter_labels = discover_job_pages(config)
            print(f"job: {job_path}")
            print(f"output: {config.output_path}")
            print(f"sources: {1 + len(config.extra_sources)}")
            print(f"bookmarks: {config.bookmark_mode}")
            print(f"compress: {config.compress} dpi={config.dpi} rotate={config.rotate}")
            print(f"page_size: {config.page_size}")
            print(f"pages: {len(pages)}")
            for label, start in zip(chapter_labels, chapter_starts, strict=True):
                print(f"  chapter[{start}] {label}")
            for page in pages:
                print(f"  {page.index + 1:4d}. {page.name}  ({page.path.parent.name})")
            return 0
        report = run_job(config, on_progress=_print_progress)
    except FileNotFoundError:
        print(f"bindery: job file not found: {job_path}", file=sys.stderr)
        return 4
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
        bindery 0.8.0
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

    if args[0] == "preview":
        return _cmd_preview(args[1:])

    if args[0] == "job":
        return _cmd_job(args[1:])

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
