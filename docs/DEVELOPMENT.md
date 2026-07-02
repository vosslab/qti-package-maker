# Developer guide

New-contributor on-ramp for working on `qti_package_maker`: how to set up, run
tests, add an engine, and use the maintainer scripts. Style rules live in
[PYTHON_STYLE.md](PYTHON_STYLE.md) and [REPO_STYLE.md](REPO_STYLE.md).

## Quick setup

Run scripts and tests straight from a clone by putting the repo root on
`PYTHONPATH`. The bootstrap script does this for you:

```sh
source source_me.sh
```

`source_me.sh` finds the git root and prepends it to `PYTHONPATH`, so
`import qti_package_maker` resolves without an install.

To install the package into a virtual environment instead:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r pip_requirements.txt
pip install -r pip_requirements-dev.txt
pip install -e .
```

Runtime dependencies live in `pip_requirements.txt`; developer-only tools (for
example `pytest`) live in `pip_requirements-dev.txt`. The package targets
Python 3.9+ at runtime (`requires-python` in `pyproject.toml`); day-to-day
development uses Python 3.12.

## Running the tool

The command-line entry point reads a Blackboard Question Upload (BBQ) text file
and writes one or more export formats:

```sh
source source_me.sh
python3 tools/bbq_converter.py -i bbq-example-questions.txt --all
```

See [USAGE.md](USAGE.md) for the flags and [COOKBOOK.md](COOKBOOK.md) for
multi-step conversion recipes that go beyond the single-command case.

## Test tiers

Tests live in four tiers under `tests/`. See [PYTEST_STYLE.md](PYTEST_STYLE.md)
for style and [E2E_TESTS.md](E2E_TESTS.md) for the slow tiers.

- `tests/test_*.py` fast pytest unit and integration tests. Run with
  `pytest tests/`. This is the fast lane and should finish in seconds.
- `tests/integration/` and `tests/unit/` deeper pytest checks collected by the
  same `pytest tests/` run.
- `tests/playwright/` browser-driven tests, run outside pytest. See
  [PLAYWRIGHT_USAGE.md](PLAYWRIGHT_USAGE.md).
- `tests/e2e/` non-browser whole-system runners (convention slot; run
  directly, not via pytest).

`tests/conftest.py` sets `collect_ignore = ["e2e", "playwright"]`, so the slow
tiers never enter the fast lane even if their filenames look like pytest tests.

Run the fast lane:

```sh
source source_me.sh
pytest tests/
```

## Repo-wide gates

Several pytest files are lint gates rather than behavior tests. They keep the
whole tree consistent, and a new contributor should expect them to run in the
fast lane:

- `tests/test_function_typing.py` every `def` must annotate every parameter
  (except `self`, `cls`, `*args`, `**kwargs`) and its return. Use builtin
  generics (`list`, `dict`, `tuple`) and PEP 604 unions (`X | None`); the
  `typing` module is not used.
- `tests/test_pyflakes_code_lint.py` runs pyflakes across the repo to catch
  unused imports and undefined names.
- `tests/test_ascii_compliance.py` enforces ASCII / ISO-8859-1 source. Use
  `tests/check_ascii_compliance.py` on one file, `tests/fix_ascii_compliance.py`
  to repair.
- `tests/test_markdown_links.py` checks that every local Markdown link is
  well formed and GitHub-browsable.
- `tests/test_import_dot.py`, `tests/test_import_star.py`, and
  `tests/test_import_requirements.py` enforce absolute imports, no `import *`,
  and that every third-party import is declared in a requirements file.
- `tests/test_shebangs.py`, `tests/test_indentation.py`,
  `tests/test_whitespace.py`, and `tests/test_init_files.py` cover shebang and
  executable-bit pairing, tab indentation, trailing whitespace, and minimal
  `__init__.py` files.

Run one gate directly, for example:

```sh
pytest tests/test_function_typing.py
pyflakes qti_package_maker/package_interface.py
```

## Engine smoke tests

`tests/test_all_engines.py` is the fast cross-engine smoke test. Other useful
checks:

```sh
pytest tests/test_all_engines.py
pytest tests/test_bbq_converter_all_types.py
pytest tests/test_human_readable_tables.py
```

## Adding an engine

An engine is a format adapter under `qti_package_maker/engines/<engine_name>/`
that reads external files into an `ItemBank` or writes items back out. The full
checklist, required functions, and worked examples are in
[ENGINE_AUTHORING.md](ENGINE_AUTHORING.md). Key points a new contributor should
know before starting:

- Engines are auto-discovered by scanning `qti_package_maker/engines/`; you do
  not edit a registry. A folder needs `__init__.py` and an `engine_class.py`
  with `EngineClass` to be found.
- Rendering goes through the one shared render loop,
  `BaseEngine.process_item_bank`. Do not copy the loop into your engine; pass
  its `item_transform_fn` / `post_render_fn` hooks when you need per-item media
  handling.
- Every engine declares a `media_policy` class attribute and routes images
  through `qti_package_maker/common/media_assets.py`. Do not write a private
  image scanner or policy branch. See the media contract in
  [ENGINE_AUTHORING.md](ENGINE_AUTHORING.md) and the per-engine behavior table
  in [ENGINES.md](ENGINES.md).

Verify discovery after adding an engine:

```sh
python3 -m qti_package_maker.engines.engine_registration
```

## Maintainer scripts (devel/)

`devel/` holds maintainer-only tooling; it is not product code and not part of
the fast pytest lane. See [DEVEL_README.md](../devel/DEVEL_README.md) for the
full list. Common tasks:

- Version bump: `devel/bump_version.py` sets or bumps the version across
  `pyproject.toml` and `VERSION`.
- PyPI release: `devel/submit_to_pypi.py` builds and uploads the package to
  TestPyPI or PyPI.
- Changelog tooling: `devel/rotate_changelog.py`, `devel/query_changelog.py`,
  and `devel/commit_changelog.py` share `devel/changelog_lib.py` to rotate,
  search, and draft commit messages from `CHANGELOG.md`.
- Media probe kits: `devel/build_canvas_media_probe.py`,
  `devel/build_bb_original_probe.py`, and `devel/build_ultra_media_probe.py`
  build the LMS image-import probe ZIPs described in
  [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md).
- Cleanup: `devel/dist_clean.sh` removes build artifacts and caches.

Run devel scripts through the bootstrap and pass `--help` for options:

```sh
source source_me.sh
python3 devel/bump_version.py --help
```

## Style notes

- Indent with tabs, not spaces. Keep lines around 100 characters.
- Use `#!/usr/bin/env python3` only on runnable scripts, and keep the
  executable bit in sync (checked by `tests/test_shebangs.py`).
- Document every code change in [CHANGELOG.md](CHANGELOG.md); docs-only edits
  do not require tests.

## References

- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
- [ENGINE_AUTHORING.md](ENGINE_AUTHORING.md), [ENGINES.md](ENGINES.md)
- [PYTHON_STYLE.md](PYTHON_STYLE.md), [PYTEST_STYLE.md](PYTEST_STYLE.md)
- [USAGE.md](USAGE.md), [COOKBOOK.md](COOKBOOK.md), [CHANGELOG.md](CHANGELOG.md)
