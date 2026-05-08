# Repository guidelines

Pointer file. Canonical rules live under `docs/`.

## Style and workflow

- [docs/REPO_STYLE.md](docs/REPO_STYLE.md) - repo organization and conventions.
- [docs/PYTHON_STYLE.md](docs/PYTHON_STYLE.md) - Python style (tabs, no try/except, no defaults that hide bugs).
- [docs/PYTEST_STYLE.md](docs/PYTEST_STYLE.md) - pytest style and failure triage.
- [docs/E2E_TESTS.md](docs/E2E_TESTS.md) - non-pytest end-to-end tests under `tests/e2e/` and `tests/playwright/`.
- [docs/MARKDOWN_STYLE.md](docs/MARKDOWN_STYLE.md) - Markdown conventions.
- [docs/CLAUDE_HOOK_USAGE_GUIDE.md](docs/CLAUDE_HOOK_USAGE_GUIDE.md) - Claude tool/hook behavior.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md), [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) - layout.
- [docs/ENGINES.md](docs/ENGINES.md), [docs/ENGINE_AUTHORING.md](docs/ENGINE_AUTHORING.md) - engine pattern and registry.
- [docs/USAGE.md](docs/USAGE.md), [docs/INSTALL.md](docs/INSTALL.md) - run and install.

## Repo-specific quirks

- Python site-packages at `/opt/homebrew/lib/python3.12/site-packages/`.
- Run scripts without install: `source source_me.sh` to set `PYTHONPATH`.
- Document every code change in [docs/CHANGELOG.md](docs/CHANGELOG.md). Docs-only edits do not require tests; code changes do.

## Standing user directives (verbatim)

- When in doubt, implement the changes the user asked for rather than waiting for a response; the user is not the best reader and will likely miss your request and then be confused why it was not implemented or fixed.
