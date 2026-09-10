"""Tests for progress events, resume manifest, and pipeline callbacks."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from bindery.models.config import JobConfig
from bindery.orchestration.manifest import (
    ResumeManifest,
    config_fingerprint,
    manifest_path_for,
)
from bindery.orchestration.pipeline import run_job
from bindery.orchestration.progress import ProgressEvent


def _pages(tmp_path: Path, count: int = 2) -> Path:
    source = tmp_path / "pages"
    source.mkdir()
    for i in range(count):
        Image.new("RGB", (20, 20), (i * 10, 0, 0)).save(source / f"p{i + 1}.png")
    return source


def test_progress_event_fraction() -> None:
    """Fraction clamps to [0, 1]."""
    assert ProgressEvent(stage="transform", completed=1, total=4).fraction == 0.25
    assert ProgressEvent(stage="done", completed=9, total=4).fraction == 1.0
    assert ProgressEvent(stage="done", completed=0, total=0).fraction == 1.0


def test_manifest_roundtrip(tmp_path: Path) -> None:
    """Manifests save and load."""
    path = tmp_path / "book.pdf.bindery.json"
    ResumeManifest(fingerprint="abc", page_count=3).save(path)
    loaded = ResumeManifest.load(path)
    assert loaded is not None
    assert loaded.fingerprint == "abc"
    assert loaded.page_count == 3


def test_manifest_load_missing_and_corrupt(tmp_path: Path) -> None:
    """Missing or corrupt manifests return None."""
    assert ResumeManifest.load(tmp_path / "nope.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert ResumeManifest.load(bad) is None


def test_manifest_path_for() -> None:
    """Sidecar sits next to the PDF."""
    assert manifest_path_for(Path("a/book.pdf")).name == "book.pdf.bindery.json"


def test_config_fingerprint_stable_and_sensitive(tmp_path: Path) -> None:
    """Same inputs same hash; changing dpi changes hash."""
    cfg = JobConfig(source_dir=tmp_path / "pages", output_path=tmp_path / "book.pdf")
    a = config_fingerprint(cfg, ["a.png"])
    b = config_fingerprint(cfg, ["a.png"])
    assert a == b
    cfg2 = JobConfig(
        source_dir=cfg.source_dir,
        output_path=cfg.output_path,
        dpi=cfg.dpi + 1,
    )
    assert config_fingerprint(cfg2, ["a.png"]) != a
    assert config_fingerprint(cfg, ["b.png"]) != a


def test_run_job_emits_progress_stages(tmp_path: Path) -> None:
    """discover/transform/assemble/done are observed in order."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    events: list[ProgressEvent] = []
    run_job(JobConfig(source_dir=source, output_path=out), on_progress=events.append)
    stages = [e.stage for e in events]
    assert stages[0] == "discover"
    assert "transform" in stages
    assert "assemble" in stages
    assert stages[-1] == "done"


def test_run_job_skips_when_up_to_date(tmp_path: Path) -> None:
    """Second identical run is a no-op skip."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    first = run_job(JobConfig(source_dir=source, output_path=out))
    assert first.skipped is False
    mtime = out.stat().st_mtime_ns
    second = run_job(JobConfig(source_dir=source, output_path=out))
    assert second.skipped is True
    assert out.stat().st_mtime_ns == mtime


def test_run_job_force_rebuilds(tmp_path: Path) -> None:
    """force=True rebuilds even when up to date."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    run_job(JobConfig(source_dir=source, output_path=out))
    report = run_job(JobConfig(source_dir=source, output_path=out, force=True))
    assert report.skipped is False


def test_run_job_rebuilds_when_config_changes(tmp_path: Path) -> None:
    """A config change invalidates the resume skip."""
    source = _pages(tmp_path)
    out = tmp_path / "book.pdf"
    run_job(JobConfig(source_dir=source, output_path=out))
    report = run_job(JobConfig(source_dir=source, output_path=out, grayscale=True))
    assert report.skipped is False
