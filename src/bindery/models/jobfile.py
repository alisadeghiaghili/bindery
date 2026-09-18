"""Multi-source and job-file models for bindery."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bindery.exceptions import BinderyValidationError

__all__ = ["SourceSpec", "load_job_file"]

_BOOKMARK_MODES = frozenset({"none", "filenames", "chapters"})


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """One source directory contribution to an assemble job.

    Attributes:
        path: Directory containing page images.
        page_names: Optional explicit order within this source.
        exclude: Optional file names to drop from this source.

    Examples:
        >>> SourceSpec(path=Path("ch1")).exclude is None
        True
    """

    path: Path
    page_names: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        """Coerce path and validate name lists.

        Raises:
            BinderyValidationError: On empty names or duplicates within pages.
        """
        object.__setattr__(self, "path", Path(self.path))
        if self.page_names is not None:
            names = tuple(str(n) for n in self.page_names)
            if any(not n for n in names):
                raise BinderyValidationError("page_names must be non-empty")
            if len(set(names)) != len(names):
                raise BinderyValidationError("page_names must not contain duplicates")
            object.__setattr__(self, "page_names", names)
        if self.exclude is not None:
            excl = tuple(str(n) for n in self.exclude)
            if any(not n for n in excl):
                raise BinderyValidationError("exclude must be non-empty names")
            object.__setattr__(self, "exclude", excl)


def _as_str_list(value: object, field: str) -> tuple[str, ...] | None:
    """Coerce a job-file list field to ``tuple[str, ...] | None``.

    Args:
        value: Raw JSON/TOML value.
        field: Field name for error messages.

    Returns:
        tuple[str, ...] | None: Normalized list or ``None``.

    Raises:
        BinderyValidationError: If the value is not a list of strings.

    Examples:
        >>> _as_str_list(None, "pages") is None
        True
        >>> _as_str_list(["a.png"], "pages")
        ('a.png',)
    """
    if value is None:
        return None
    if not isinstance(value, list | tuple):
        raise BinderyValidationError(f"{field} must be a list of strings")
    return tuple(str(item) for item in value)


def _parse_source_entry(entry: object, index: int) -> SourceSpec:
    """Parse one ``sources[]`` entry from a job file.

    Args:
        entry: Either a path string or a mapping with ``path``.
        index: Zero-based index used in error messages.

    Returns:
        SourceSpec: Parsed source contribution.

    Raises:
        BinderyValidationError: On invalid shape or keys.

    Examples:
        >>> _parse_source_entry("ch1", 0).path.as_posix()
        'ch1'
    """
    if isinstance(entry, str | Path):
        return SourceSpec(path=Path(entry))
    if not isinstance(entry, dict):
        raise BinderyValidationError(f"sources[{index}] must be a path or mapping")
    data: dict[str, Any] = entry
    if "path" not in data:
        raise BinderyValidationError(f"sources[{index}] requires path")
    unknown = set(data) - {"path", "pages", "exclude"}
    if unknown:
        raise BinderyValidationError(f"sources[{index}] unknown keys: {sorted(unknown)}")
    return SourceSpec(
        path=Path(str(data["path"])),
        page_names=_as_str_list(data.get("pages"), f"sources[{index}].pages"),
        exclude=_as_str_list(data.get("exclude"), f"sources[{index}].exclude"),
    )


def load_job_file(path: Path) -> dict[str, Any]:
    """Load a bindery job file (``.toml`` or ``.json``).

    Args:
        path: Job file path.

    Returns:
        dict[str, Any]: Normalized job mapping with:
            ``output`` (str), ``sources`` (list[SourceSpec]),
            ``bookmark_mode`` (str), plus optional scalar job options.

    Raises:
        BinderyValidationError: On unreadable file, bad format, or invalid fields.
        FileNotFoundError: If ``path`` does not exist.

    Examples:
        >>> callable(load_job_file)
        True
    """
    job_path = Path(path)
    if not job_path.is_file():
        raise FileNotFoundError(job_path)
    suffix = job_path.suffix.lower()
    try:
        raw_bytes = job_path.read_bytes()
        if suffix == ".json":
            data = json.loads(raw_bytes.decode("utf-8"))
        elif suffix in {".toml", ".tml"}:
            data = tomllib.loads(raw_bytes.decode("utf-8"))
        else:
            raise BinderyValidationError(f"job file must be .toml or .json, got {suffix!r}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise BinderyValidationError(f"cannot parse job file {job_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise BinderyValidationError("job file root must be a mapping")

    if "output" not in data:
        raise BinderyValidationError("job file requires output")
    sources_raw = data.get("sources")
    if not sources_raw:
        raise BinderyValidationError("job file requires non-empty sources")
    if not isinstance(sources_raw, list):
        raise BinderyValidationError("sources must be a list")
    sources = tuple(_parse_source_entry(entry, i) for i, entry in enumerate(sources_raw))

    bookmark_mode = str(data.get("bookmarks", data.get("bookmark_mode", "none"))).strip().lower()
    if bookmark_mode not in _BOOKMARK_MODES:
        raise BinderyValidationError(
            f"bookmarks must be one of {sorted(_BOOKMARK_MODES)}, got {bookmark_mode!r}"
        )

    allowed = {
        "output",
        "sources",
        "title",
        "author",
        "dpi",
        "margin",
        "grayscale",
        "stamp",
        "rotate",
        "page_size",
        "compress",
        "jpeg_quality",
        "force",
        "bookmarks",
        "bookmark_mode",
    }
    unknown = set(data) - allowed
    if unknown:
        raise BinderyValidationError(f"job file unknown keys: {sorted(unknown)}")

    normalized: dict[str, Any] = {
        "output": str(data["output"]),
        "sources": sources,
        "title": data.get("title"),
        "author": data.get("author"),
        "dpi": data.get("dpi", 300),
        "margin": data.get("margin", 0),
        "grayscale": bool(data.get("grayscale", False)),
        "stamp": bool(data.get("stamp", False)),
        "rotate": data.get("rotate", 0),
        "page_size": data.get("page_size"),
        "compress": data.get("compress", "lossless"),
        "jpeg_quality": data.get("jpeg_quality", 85),
        "force": bool(data.get("force", False)),
        "bookmark_mode": bookmark_mode,
    }
    return normalized
