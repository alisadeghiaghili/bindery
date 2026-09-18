"""Build a JobConfig from a bindery job file mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.models.jobfile import load_job_file

__all__ = ["job_config_from_file", "job_config_from_mapping"]


def job_config_from_mapping(data: dict[str, Any], *, base_dir: Path | None = None) -> JobConfig:
    """Create a :class:`JobConfig` from a normalized job mapping.

    Args:
        data: Mapping from :func:`bindery.models.jobfile.load_job_file`.
        base_dir: Optional directory used to resolve relative paths.

    Returns:
        JobConfig: Job settings ready for :func:`run_job`.

    Examples:
        >>> callable(job_config_from_mapping)
        True
    """
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    sources = data["sources"]
    primary = sources[0]
    extras = tuple(
        (root / spec.path) if not spec.path.is_absolute() else spec.path for spec in sources[1:]
    )
    first_path = (root / primary.path) if not primary.path.is_absolute() else primary.path
    output = Path(data["output"])
    if not output.is_absolute():
        output = root / output
    return JobConfig(
        source_dir=first_path,
        output_path=output,
        margins=MarginSpec.uniform(int(data.get("margin", 0))),
        grayscale=bool(data.get("grayscale", False)),
        stamp_page_numbers=bool(data.get("stamp", False)),
        dpi=int(data.get("dpi", 300)),
        force=bool(data.get("force", False)),
        title=data.get("title"),
        author=data.get("author"),
        rotate=int(data.get("rotate", 0)),
        page_size=data.get("page_size"),
        compress=str(data.get("compress", "lossless")),
        jpeg_quality=int(data.get("jpeg_quality", 85)),
        extra_sources=extras,
        sources=tuple(
            type(spec)(
                path=(root / spec.path) if not spec.path.is_absolute() else spec.path,
                page_names=spec.page_names,
                exclude=spec.exclude,
            )
            for spec in sources
        ),
        bookmark_mode=str(data.get("bookmark_mode", "none")),
    )


def job_config_from_file(path: Path) -> JobConfig:
    """Load a job file and build a :class:`JobConfig`.

    Args:
        path: Path to a ``.toml`` or ``.json`` job file.

    Returns:
        JobConfig: Job settings with paths resolved against the job file parent.

    Examples:
        >>> callable(job_config_from_file)
        True
    """
    job_path = Path(path)
    data = load_job_file(job_path)
    return job_config_from_mapping(data, base_dir=job_path.parent)
