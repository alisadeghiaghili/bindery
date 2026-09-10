"""PDF assembly via img2pdf (lossless page embed) + pypdf (metadata)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import img2pdf
from pypdf import PdfReader

from bindery.exceptions import BinderyIOError, BinderyValidationError

__all__ = ["write_pdf"]

LayoutFun = Callable[[int, int, tuple[float, float]], tuple[float, float, float, float]]


def _layout_for_dpi(dpi: int) -> LayoutFun:
    """Build an img2pdf ``layout_fun`` that forces page size from ``dpi``.

    img2pdf 0.6.x does not accept a ``dpi=`` convert kwarg; page geometry comes
    from image metadata (default 96) unless a layout function overrides it.

    Args:
        dpi: Pixels per inch used to convert pixel size to PDF points.

    Returns:
        LayoutFun: ``(width_px, height_px, ndpi) -> (page_w, page_h, img_w, img_h)``.

    Examples:
        >>> layout = _layout_for_dpi(100)
        >>> layout(100, 50, (96.0, 96.0))
        (72.0, 36.0, 72.0, 36.0)
        >>> layout(10, 10, (96.0, 96.0))
        (3.0, 3.0, 3.0, 3.0)
    """

    def layout(
        imgwidthpx: int,
        imgheightpx: int,
        ndpi: tuple[float, float],
    ) -> tuple[float, float, float, float]:
        del ndpi  # image dpi is intentionally ignored
        width_pt = imgwidthpx * 72.0 / dpi
        height_pt = imgheightpx * 72.0 / dpi
        # pikepdf/PDF viewers reject pages smaller than 3pt on either axis.
        if width_pt < 3.0 or height_pt < 3.0:
            scale = max(3.0 / max(width_pt, 1e-9), 3.0 / max(height_pt, 1e-9))
            width_pt *= scale
            height_pt *= scale
        return (width_pt, height_pt, width_pt, height_pt)

    return layout


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
        dpi: Pixels per inch used for PDF page geometry. Must be > 0.
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
        raw_pdf: bytes = img2pdf.convert(
            resolved,
            layout_fun=_layout_for_dpi(dpi),
            title=title,
            author=author,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise BinderyIOError(f"PDF conversion failed: {exc}") from exc

    try:
        output.write_bytes(raw_pdf)
    except OSError as exc:
        raise BinderyIOError(f"cannot write PDF: {output}: {exc}") from exc

    reader = PdfReader(output)
    if len(reader.pages) != len(resolved):
        raise BinderyIOError(
            f"PDF page count mismatch: wrote {len(reader.pages)}, expected {len(resolved)}"
        )
    return output
