# Repository guidelines

Pointer file. Canonical rules live under `docs/`. Reference by bare path.

## Style and workflow

- `docs/REPO_STYLE.md` - repo organization and conventions.
- `docs/PYTHON_STYLE.md` - Python style (tabs, no try/except, no hiding-bug defaults).
- `docs/PYTEST_STYLE.md` - pytest style and failure triage.
- `docs/E2E_TESTS.md` - non-pytest end-to-end tests under `tests/e2e/`, `tests/playwright/`.
- `docs/MARKDOWN_STYLE.md` - Markdown conventions.
- `docs/CLAUDE_HOOK_USAGE_GUIDE.md` - Claude tool/hook behavior.

## Architecture and engines

- `docs/CODE_ARCHITECTURE.md`, `docs/FILE_STRUCTURE.md` - layout and data flow.
- `docs/ENGINES.md`, `docs/ENGINE_AUTHORING.md` - engine pattern, registry, media_policy contract.
- `docs/USAGE.md`, `docs/INSTALL.md`, `docs/COOKBOOK.md` - run, install, worked examples.
- `docs/FORMATS.md`, `docs/QUESTION_TYPES.md` - I/O formats and question types.
- `docs/TROUBLESHOOTING.md`, `docs/DEVELOPMENT.md`, `docs/ROADMAP.md`, `docs/TODO.md` - support docs.

## Repo-specific quirks

- Python site-packages at `/opt/homebrew/lib/python3.12/site-packages/`.
- Run scripts without install: `source source_me.sh` sets `PYTHONPATH`.
- Test cheat-line: `source source_me.sh && pytest tests/`.
- Document every code change in `docs/CHANGELOG.md`. Docs-only edits skip tests; code changes need them.

## Standing user directives (verbatim)

- When in doubt, implement the changes the user asked for rather than waiting for a response; the user is not the best reader and will likely miss your request and then be confused why it was not implemented or fixed.
