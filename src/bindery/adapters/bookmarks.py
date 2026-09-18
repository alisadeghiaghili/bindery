"""PDF outline/bookmark helpers built on pypdf."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from bindery.exceptions import BinderyIOError, BinderyValidationError

__all__ = ["apply_bookmarks", "bookmark_titles"]


def bookmark_titles(
    mode: str,
    page_files: list[str],
    chapter_starts: list[int],
    chapter_labels: list[str],
) -> list[str] | None:
    """Build outline titles for each page, or ``None`` when disabled.

    Args:
        mode: ``none``, ``filenames``, or ``chapters``.
        page_files: Page file names in assemble order.
        chapter_starts: Zero-based page indices that begin a chapter.
        chapter_labels: Labels for each chapter start (same length as starts).

    Returns:
        list[str] | None: One title per page, or ``None`` if mode is ``none``.

    Raises:
        BinderyValidationError: On unknown mode or mismatched chapter lists.

    Examples:
        >>> bookmark_titles("none", ["a.png"], [0], ["ch1"]) is None
        True
        >>> bookmark_titles("filenames", ["a.png"], [], [])
        ['a.png']
    """
    normalized = str(mode).strip().lower()
    if normalized == "none":
        return None
    if len(chapter_starts) != len(chapter_labels):
        raise BinderyValidationError("chapter_starts and chapter_labels length mismatch")
    if normalized == "filenames":
        return list(page_files)
    if normalized == "chapters":
        starts = {int(i): label for i, label in zip(chapter_starts, chapter_labels, strict=True)}
        titles: list[str] = []
        current = chapter_labels[0] if chapter_labels else "Document"
        for index in range(len(page_files)):
            if index in starts:
                current = starts[index]
            titles.append(current)
        return titles
    raise BinderyValidationError(f"bookmark mode must be none|filenames|chapters, got {mode!r}")


def apply_bookmarks(pdf_path: Path, titles: list[str]) -> None:
    """Write PDF outline items pointing at pages 0..n-1.

    Args:
        pdf_path: Existing PDF to update in place.
        titles: One outline title per page.

    Raises:
        BinderyValidationError: If ``titles`` is empty.
        BinderyIOError: If the PDF cannot be read or rewritten.

    Examples:
        >>> callable(apply_bookmarks)
        True
    """
    if not titles:
        raise BinderyValidationError("apply_bookmarks requires at least one title")
    path = Path(pdf_path)
    try:
        reader = PdfReader(path)
        writer = PdfWriter()
        writer.append(reader)
        if len(writer.pages) != len(titles):
            raise BinderyValidationError(
                f"bookmark count {len(titles)} != page count {len(writer.pages)}"
            )
        for index, title in enumerate(titles):
            writer.add_outline_item(title, index)
        tmp = path.with_suffix(path.suffix + ".bindery-tmp")
        with tmp.open("wb") as handle:
            writer.write(handle)
        tmp.replace(path)
    except BinderyValidationError:
        raise
    except OSError as exc:
        raise BinderyIOError(f"cannot write bookmarks for {path}: {exc}") from exc
