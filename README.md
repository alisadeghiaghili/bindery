# bindery

Assemble image folders into a single, clean PDF document.

**Status:** v0.6.0 — CLI + desktop GUI on the same pipeline. Windows `bindery.exe` is published on Releases.

## What this is

`bindery` takes a directory of page images (PNG/JPEG/WebP/TIFF/BMP) and produces one multi-page PDF, with optional margins, grayscale, page stamps, and title metadata. Processing is local.

## Non-goals

These are permanent product boundaries, not backlog:

- **No scraping.** bindery does not fetch content from websites, ebook platforms, or any remote service. Inputs must be files you already have the right to use.
- **No DRM circumvention.** It will not open protected commercial ebook formats or bypass access controls.
- **No cloud dependency.** All processing is local.

If a workflow needs the above, it belongs in a different product.

## Install

### Standalone Windows executable

Download `bindery.exe` from [Releases](https://github.com/alisadeghiaghili/bindery/releases) (asset is versioned as `bindery-<version>-windows-x64.exe`).

### From source

```bash
uv sync --group dev
uv run bindery --version
```

Requires Python 3.12+.

## Usage

```bash
bindery build ./pages -o book.pdf --margin 8 --grayscale --stamp --dpi 300
bindery build ./pages -o book.pdf --force   # rebuild even if up to date
bindery inspect ./pages
bindery doctor
bindery gui
bindery --version
bindery --help
```

A sidecar `book.pdf.bindery.json` records a config fingerprint. Re-running an identical job prints `Up to date` and skips work unless you pass `--force`.

Exit codes: `0` success, `2` usage, `3` validation, `4` I/O.

## Development

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
uv run python tools/doc_audit.py --path src/bindery --style google --require-example
```

Build the Windows executable locally:

```bash
uv run pyinstaller --clean --noconfirm bindery.spec
dist\bindery.exe --version
```

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Author

Ali Sadeghi Aghili
