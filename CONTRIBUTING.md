# Contributing

## Ground rules

1. Every public claim in docs must match running code. Do not mark features done without command output.
2. TDD for domain and adapters: write the failing test first, then implement.
3. Keep pull requests reviewable: one coherent theme per PR, with a clear release note. Batch related fixes when they share that theme; do not pad unrelated work to hit a size target.
4. Conventional Commits with a scope, for example `feat(domain): natural-sort filenames`.
5. No `except Exception:` widen, no skipped tests to go green, no silent failures. GUI smoke tests may skip when Tcl/Tk is absent; product modules must still import without optional UI stacks.
6. Google-style docstrings with `Args`, `Returns`, `Raises`, and a runnable `Example` on every public symbol.

## Gates before merge

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
uv run python tools/doc_audit.py --path src/bindery --style google --require-example
```

All must pass. CI runs the same commands.

## Branching

- `main` is releasable.
- Feature work: `feat/<stage-or-topic>` → PR → merge → delete branch.
- Fix work: `fix/<issue>`.

## Releases

After merging a stage PR:

1. Bump version in `pyproject.toml` and `src/bindery/__init__.py`.
2. Update `CHANGELOG.md`.
3. Tag `vX.Y.Z` and publish a GitHub Release.
