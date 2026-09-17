"""Tests for progress events, resume manifest, and pipeline callbacks."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.orchestration.manifest import (
    ResumeManifest,
    config_fingerprint,
    manifest_path_for,
    page_identity,
)
from bindery.orchestration.pipeline import _transform_page, run_job
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
    """Same inputs same hash; changing dpi or page content changes hash."""
    cfg = JobConfig(source_dir=tmp_path / "pages", output_path=tmp_path / "book.pdf")
    page = tmp_path / "a.png"
    page.write_bytes(b"one")
    identity = page_identity(page)
    a = config_fingerprint(cfg, [identity])
    b = config_fingerprint(cfg, [identity])
    assert a == b
    cfg2 = JobConfig(
        source_dir=cfg.source_dir,
        output_path=cfg.output_path,
        dpi=cfg.dpi + 1,
    )
    assert config_fingerprint(cfg2, [identity]) != a
    page.write_bytes(b"two-longer")
    assert config_fingerprint(cfg, [page_identity(page)]) != a
    assert config_fingerprint(cfg, [{**identity, "name": "b.png"}]) != a


def test_config_fingerprint_includes_source_and_output_paths(tmp_path: Path) -> None:
    """Different source or output paths must not share a resume fingerprint."""
    identity = {"name": "p1.png", "size": 10, "mtime_ns": 123}
    cfg_a = JobConfig(source_dir=tmp_path / "src_a", output_path=tmp_path / "out_a.pdf")
    cfg_b = JobConfig(source_dir=tmp_path / "src_b", output_path=tmp_path / "out_a.pdf")
    cfg_c = JobConfig(source_dir=tmp_path / "src_a", output_path=tmp_path / "out_b.pdf")
    fingerprint_a = config_fingerprint(cfg_a, [identity])
    assert config_fingerprint(cfg_b, [identity]) != fingerprint_a
    assert config_fingerprint(cfg_c, [identity]) != fingerprint_a


def test_run_job_rebuilds_when_page_content_changes(tmp_path: Path) -> None:
    """Rewriting an image under the same name invalidates resume skip."""
    source = _pages(tmp_path, count=1)
    page = next(source.iterdir())
    out = tmp_path / "book.pdf"
    first = run_job(JobConfig(source_dir=source, output_path=out))
    assert first.skipped is False
    Image.new("RGB", (24, 24), (0, 90, 200)).save(page)
    second = run_job(JobConfig(source_dir=source, output_path=out))
    assert second.skipped is False


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


def test_transform_grayscale_keeps_mode_l(tmp_path: Path) -> None:
    """Grayscale jobs write intermediate PNGs as mode L, not RGB."""
    source = tmp_path / "pages"
    source.mkdir()
    page_path = source / "p1.png"
    Image.new("RGB", (20, 20), (200, 0, 0)).save(page_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    cfg = JobConfig(
        source_dir=source,
        output_path=tmp_path / "book.pdf",
        grayscale=True,
        margins=MarginSpec.uniform(2),
        stamp_page_numbers=True,
    )
    from bindery.models.page import PageFile
    from bindery.orchestration.pipeline import _STAMP_FOOTER_BAND

    out = _transform_page(PageFile(path=page_path, index=0), cfg, work_dir)
    with Image.open(out) as image:
        assert image.mode == "L"
        # bottom band is raised to the stamp footer minimum
        assert image.size == (24, 20 + 2 + _STAMP_FOOTER_BAND)


def test_transform_stamp_with_zero_margin_reserves_footer_band(tmp_path: Path) -> None:
    """Stamp jobs pad a footer band so numbers never overlay page content."""
    source = tmp_path / "pages"
    source.mkdir()
    page_path = source / "p1.png"
    # Full-bleed non-white content: overlay would be visible on content pixels.
    Image.new("RGB", (40, 40), (10, 20, 30)).save(page_path)
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    cfg = JobConfig(
        source_dir=source,
        output_path=tmp_path / "book.pdf",
        margins=MarginSpec.uniform(0),
        stamp_page_numbers=True,
    )
    from bindery.models.page import PageFile
    from bindery.orchestration.pipeline import _STAMP_FOOTER_BAND

    out = _transform_page(PageFile(path=page_path, index=0), cfg, work_dir)
    with Image.open(out) as image:
        assert image.size == (40, 40 + _STAMP_FOOTER_BAND)
        # Footer band starts after the original content row range.
        footer_top = 40
        row = [image.getpixel((x, footer_top + 2)) for x in range(40)]
        assert any(pixel == (255, 255, 255) for pixel in row)
