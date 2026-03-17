# Contributing

This repo keeps a strict boundary between public product files and local-only
research artifacts.

## Public Files

Normal commits should be limited to:

- [custom_components/came_connect](/home/d0m/Projects/gtapps/came_connect/custom_components/came_connect)
- [tests](/home/d0m/Projects/gtapps/came_connect/tests)
- [README.md](/home/d0m/Projects/gtapps/came_connect/README.md)
- [CHANGELOG.md](/home/d0m/Projects/gtapps/came_connect/CHANGELOG.md)
- [docs/user](/home/d0m/Projects/gtapps/came_connect/docs/user)
- sanitized maintainer docs under [docs/maintainers](/home/d0m/Projects/gtapps/came_connect/docs/maintainers)

## Local-Only Files

Do not commit anything under `.local/`.

That includes:

- raw captures
- protocol investigation notes
- reverse-engineering scripts
- AI workflow files
- planning or handoff state

## Verification

Before committing, run:

```bash
python3 -m py_compile custom_components/came_connect/*.py tests/*.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Review Guidance

- Prefer small product-facing changes over repo-wide cleanup.
- Keep tests dummy-only; never place real identifiers or credentials in test
  data.
- If a maintainer note contains live identifiers, move it to `.local/` first
  and only add a sanitized derivative back under `docs/maintainers/`.
