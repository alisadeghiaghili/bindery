# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0] - 2026-09-18

### Added

- Crop and rotate on the assemble path: `JobConfig.crop` / `JobConfig.rotate`, CLI `--crop L,T,R,B` and `--rotate DEG`.
- Fixed page geometry: `--page-size a4|letter|WIDTHxHEIGHT` (PDF points) letterboxes pages at job `dpi`.
- Compression profiles: `--compress lossless|jpeg` and `--jpeg-quality` (JPEG embed vs PNG embed).
- Explicit page order/filter: `JobConfig.page_names`, CLI `--pages` / `--exclude`.
- Multi-source chapters: `JobConfig.extra_sources` / `JobConfig.sources`, CLI `--extra-source DIR` (repeatable).
- Job files: `bindery job JOBFILE.toml|json` with optional `--dry-run` to list planned pages/chapters.
- PDF bookmarks/outline: `--bookmarks none|filenames|chapters` (GUI combo included).
- `bindery preview SOURCE -o IMAGE` writes one transformed page for inspection.
- GUI: page list with include/exclude + reorder, rotate/page-size/compress/bookmark controls, first-page preview thumbnail.
- Resume fingerprint covers crop, rotate, page size, compress, page order, extra sources, job sources, and bookmark mode.

### Changed

- Transform order is crop → rotate → pad/stamp band → grayscale → page-size letterbox → save.
- Discovery walks primary source then `extra_sources` / job-file `sources` in order, with per-source `pages`/`exclude`.

## [0.7.1] - 2026-09-18

### Changed

- CLI `inspect` uses the same argparse path as `build` (exit codes unchanged: 0/2/3/4). Unknown flags after SOURCE are usage errors.

### Added

- Coverage for CLI usage errors, doctor missing-dependency / failed-API report, and PDF write-failure path.
- Windows release executable `bindery-<version>-windows-x64.exe` is attached to GitHub Releases.

## [0.7.0] - 2026-09-18

### Added

- CLI `--title` / `--author` and GUI Title/Author fields write PDF document metadata.
- `JobConfig.title` / `JobConfig.author` (blank strings normalize to `None`).
- Resume fingerprint includes title, author, resolved `source_dir`, and resolved `output_path`.
- Stamp jobs reserve a footer band when bottom margin is thinner than `_STAMP_FOOTER_BAND` so numbers do not overlay page content.
- Automated GUI cancel-control tests (flag set, UI reset on cancel/error).

### Fixed

- Resume fingerprint now includes page size and mtime, so rewriting an image under the same filename rebuilds the PDF.
- `--grayscale` / `JobConfig.grayscale` keeps intermediate pages as mode `L` instead of converting back to RGB.
- Natural sort is total: `page_02.png` vs `page_2.png` no longer depend on directory iteration order.
- `JobConfig` and `ensure_source_output_distinct` compare resolved paths (`pages` vs `./pages`).
- Transform workdir uses an isolated system temp directory instead of a predictable path next to the output PDF.
- `bindery doctor` reports `sys.platform` instead of `platform.platform()`, which can fatal-crash on Windows WMI probes.
- PyInstaller spec no longer lists undeclared `pikepdf` as a hidden import.
- `tools/doc_audit.py` documentation no longer references missing `ENGINEERING-STANDARDS.md` / `claim_audit.py`.

### Changed

- Package root exports `JobConfig`, `JobReport`, and `run_job`.
- CLI `build` parses options with `argparse` (exit codes unchanged: 0/2/3/4).
- CI quality gates run on Ubuntu and Windows, Python 3.12 and 3.13.
- Coverage policy: `fail_under=90` measures package surface excluding `gui.py` (tkinter shell; smoke-tested when Tcl/Tk loads).

## [0.6.0] - 2026-09-10

### Added

- Desktop GUI (`bindery gui`) using tkinter, stdlib only.
- GUI calls the same `run_job` pipeline; worker thread + progress queue.
- Cooperative cancel, progress bar, log panel, margin/dpi/options form.

## [0.5.0] - 2026-09-10

### Added

- `bindery inspect SOURCE` and `bindery doctor`.

## [0.4.0] - 2026-09-10

### Added

- Progress events, resume manifest, `--force`, timing log.

## [0.3.1] - 2026-09-10

### Fixed

- PDF page geometry honors dpi via img2pdf `layout_fun`.

## [0.3.0] - 2026-09-10

### Added

- Adapters, orchestration, CLI `build`, Windows exe.

## [0.2.0] - 2026-09-10

### Added

- Domain models and project scaffolding.

## [0.1.0] - 2026-09-10

### Added

- Initial package skeleton.

[Unreleased]: https://github.com/alisadeghiaghili/bindery/compare/v0.8.0...HEAD
[0.8.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/alisadeghiaghili/bindery/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/alisadeghiaghili/bindery/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/alisadeghiaghili/bindery/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/alisadeghiaghili/bindery/releases/tag/v0.1.0
