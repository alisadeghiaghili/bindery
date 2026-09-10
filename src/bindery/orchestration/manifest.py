"""Job report and resume manifest helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bindery.models.config import JobConfig
from bindery.models.page import PageFile

__all__ = [
    "JobReport",
    "ResumeManifest",
    "config_fingerprint",
    "manifest_path_for",
]


@dataclass(frozen=True, slots=True)
class JobReport:
    """Outcome of a completed assemble job.

    Attributes:
        output_path: Path of the written PDF.
        page_count: Number of pages written.
        pages: Discovered page files in natural order.
        skipped: True when an up-to-date output was reused.

    Examples:
        >>> from pathlib import Path
        >>> report = JobReport(output_path=Path("book.pdf"), page_count=2, pages=(), skipped=False)
        >>> report.page_count
        2
    """

    output_path: Path
    page_count: int
    pages: tuple[PageFile, ...]
    skipped: bool = False


def manifest_path_for(output_path: Path) -> Path:
    """Return the sidecar manifest path for ``output_path``.

    Args:
        output_path: Final PDF path.

    Returns:
        Path: ``<output>.bindery.json`` next to the PDF.

    Examples:
        >>> from pathlib import Path
        >>> manifest_path_for(Path("book.pdf")).name
        'book.pdf.bindery.json'
    """
    return Path(output_path).with_suffix(Path(output_path).suffix + ".bindery.json")


def config_fingerprint(config: JobConfig, page_names: list[str]) -> str:
    """Hash job settings and ordered page names for resume decisions.

    Args:
        config: Active job configuration.
        page_names: Page file names in assemble order.

    Returns:
        str: Hex digest of a stable JSON payload.

    Examples:
        >>> from pathlib import Path
        >>> from bindery.models.config import JobConfig
        >>> cfg = JobConfig(source_dir=Path("pages"), output_path=Path("book.pdf"))
        >>> len(config_fingerprint(cfg, ["a.png"])) == 64
        True
    """
    payload: dict[str, Any] = {
        "dpi": config.dpi,
        "grayscale": config.grayscale,
        "stamp_page_numbers": config.stamp_page_numbers,
        "margins": config.margins.as_inset(),
        "pages": list(page_names),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True, slots=True)
class ResumeManifest:
    """Sidecar record used to skip redundant rebuilds.

    Attributes:
        fingerprint: Output of :func:`config_fingerprint`.
        page_count: Number of pages in the existing PDF.

    Examples:
        >>> ResumeManifest(fingerprint="abc", page_count=3).page_count
        3
    """

    fingerprint: str
    page_count: int

    def save(self, path: Path) -> None:
        """Write this manifest as JSON.

        Args:
            path: Destination JSON path.

        Examples:
            >>> import tempfile
            >>> from pathlib import Path
            >>> p = Path(tempfile.mkdtemp()) / "m.json"
            >>> ResumeManifest(fingerprint="x", page_count=1).save(p)
            >>> p.is_file()
            True
        """
        payload = {"fingerprint": self.fingerprint, "page_count": self.page_count}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ResumeManifest | None:
        """Load a manifest if present and valid.

        Args:
            path: JSON path produced by :meth:`save`.

        Returns:
            ResumeManifest | None: Parsed manifest, or ``None`` if missing/corrupt.

        Examples:
            >>> callable(ResumeManifest.load)
            True
        """
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(fingerprint=str(data["fingerprint"]), page_count=int(data["page_count"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None
