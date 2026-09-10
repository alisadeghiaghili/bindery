# bindery

Assemble image folders and PDF pages into a single, clean PDF document.

**Status:** v0.1.0 — toolchain and package skeleton only. No transform pipeline yet.

## What this is

`bindery` takes a directory of page images (PNG/JPEG/WebP) or mixed inputs and produces one multi-page PDF, with optional crop/margins, grayscale, page stamps, and metadata. It is a local document-assembly tool.

## Non-goals

These are permanent product boundaries, not backlog:

- **No scraping.** bindery does not fetch content from websites, ebook platforms, or any remote service. Inputs must be files you already have the right to use.
- **No DRM circumvention.** It will not open protected commercial ebook formats or bypass access controls.
- **No cloud dependency.** All processing is local.

If a workflow needs the above, it belongs in a different product.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended)

## Install (development)

```bash
uv sync --group dev
uv run bindery --version
```

## Usage (v0.1.0)

```bash
uv run bindery --version
# bindery 0.1.0

uv run python -m bindery --help
```

Real `build` / `inspect` / `doctor` commands arrive in later 0.x releases. See [CHANGELOG](CHANGELOG.md).

## Development

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
```

Documentation gate (Google style, examples required):

```bash
uv run python tools/doc_audit.py --path src/bindery --style google --require-example
```

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Author

Ali Sadeghi Aghili
