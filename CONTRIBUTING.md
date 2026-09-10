# Contributing

## Ground rules

1. Every public claim in docs must match running code. Do not mark features done without command output.
2. TDD for domain and adapters: write the failing test first, then implement.
3. One human-week of work per pull request when possible. Keep PRs reviewable.
4. Conventional Commits with a scope, for example `feat(domain): natural-sort filenames`.
5. No `except Exception:` widen, no skipped tests to go green, no silent failures.
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
