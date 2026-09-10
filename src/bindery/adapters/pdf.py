"""PDF assembly via img2pdf (lossless page embed) + pypdf (metadata)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import img2pdf
from pypdf import PdfReader, PdfWriter

from bindery.exceptions import BinderyIOError, BinderyValidationError

__all__ = ["write_pdf"]


def write_pdf(
    image_paths: list[Path],
    output_path: Path,
    *,
    dpi: int = 300,
    title: str | None = None,
    author: str | None = None,
) -> Path:
    """Assemble images into a single multi-page PDF in one write.

    Pages are embedded losslessly. Metadata is applied in a second in-memory
    pass only when ``title`` or ``author`` is set — the on-disk PDF is written
    once (plus a replace when metadata is added).

    Args:
        image_paths: Source images in page order. Must be non-empty.
        output_path: Destination PDF path. Parent directories are created.
        dpi: Resolution metadata for the PDF. Must be > 0.
        title: Optional document title metadata.
        author: Optional document author metadata.

    Returns:
        Path: The output path written.

    Raises:
        BinderyValidationError: If ``image_paths`` is empty or dpi is invalid.
        BinderyIOError: If a source image cannot be read or the write fails.

    Examples:
        >>> from pathlib import Path
        >>> from PIL import Image
        >>> import tempfile
        >>> d = Path(tempfile.mkdtemp())
        >>> p = d / "a.png"
        >>> Image.new("RGB", (10, 10), (0, 0, 0)).save(p)
        >>> out = write_pdf([p], d / "book.pdf", title="T")
        >>> out.is_file()
        True
    """
    if not image_paths:
        raise BinderyValidationError("write_pdf requires at least one image")
    if not isinstance(dpi, int) or isinstance(dpi, bool) or dpi <= 0:
        raise BinderyValidationError(f"dpi must be a positive int, got {dpi!r}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    resolved: list[str] = []
    for path in image_paths:
        candidate = Path(path)
        if not candidate.is_file():
            raise BinderyIOError(f"cannot read image for PDF: {candidate}")
        resolved.append(str(candidate))

    try:
        raw_pdf: bytes = img2pdf.convert(resolved, dpi=(dpi, dpi))
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise BinderyIOError(f"PDF conversion failed: {exc}") from exc

    if title is None and author is None:
        try:
            output.write_bytes(raw_pdf)
        except OSError as exc:
            raise BinderyIOError(f"cannot write PDF: {output}: {exc}") from exc
        return output

    writer = PdfWriter()
    writer.append(io.BytesIO(raw_pdf))
    metadata: dict[str, Any] = {}
    if title is not None:
        metadata["/Title"] = title
    if author is not None:
        metadata["/Author"] = author
    writer.add_metadata(metadata)
    try:
        with output.open("wb") as handle:
            writer.write(handle)
    except OSError as exc:
        raise BinderyIOError(f"cannot write PDF: {output}: {exc}") from exc

    reader = PdfReader(output)
    if len(reader.pages) != len(resolved):
        raise BinderyIOError(
            f"PDF page count mismatch: wrote {len(reader.pages)}, expected {len(resolved)}"
        )
    return output
