# Architecture

## Layering

```text
interface  →  orchestration  →  domain  ←  adapters  ←  models
```

Dependencies point inward only.

| Layer | Responsibility | May import |
|---|---|---|
| `interface` | CLI / GUI, argument parsing, human-facing errors | orchestration, models, exceptions |
| `orchestration` | pipeline steps, progress, resume | domain, adapters, models, exceptions |
| `domain` | pure geometry, ordering, validation | models, exceptions |
| `adapters` | filesystem, Pillow, PDF writers | models, exceptions |
| `models` | immutable config/page types | stdlib only |

## v0.4.0 status

Present:

- models, domain, adapters, orchestration
- CLI `build` with progress + resume (`--force` to override)
- resume sidecar fingerprint (`*.pdf.bindery.json`)
- Windows `bindery.exe` on Releases

Still missing: GUI, OCR extra, rich progress UI (tqdm/rich).

## Non-goals (permanent)

- No scraping or remote content fetch.
- No DRM circumvention.
- No mandatory cloud services.
