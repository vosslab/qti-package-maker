# File structure

## Overview
Most work happens in one Python package,
[qti_package_maker](../qti_package_maker), organized around the same hub-and-edges
shape as the code: a central item bank, reader/writer engines around it, and shared
helper layers underneath. Start with the map below, then drop into the subtree that
matches your task. For how these pieces fit together, see
[CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md).

## Top-level layout
- [qti_package_maker](../qti_package_maker): the main Python package (all runtime code).
- [tools](../tools): command-line scripts, including the primary
  [tools/bbq_converter.py](../tools/bbq_converter.py) front end.
- [tests](../tests): pytest unit and integration tests, lint gates, and fixtures.
- [devel](../devel): developer helper scripts, including the LMS media probe kits.
- [docs](.): the documentation set (this file lives here).
- [examples](../examples): small sample packages for manual validation.
- [notes](../notes): local scratch notes.
- [AGENTS.md](../AGENTS.md): agent workflow rules and repo-specific quirks.
- [README.md](../README.md): project overview and quick start.
- [pyproject.toml](../pyproject.toml): package metadata and build configuration.
- [VERSION](../VERSION): version string kept in sync with `pyproject.toml`.
- [pip_requirements.txt](../pip_requirements.txt): runtime dependencies.
- [source_me.sh](../source_me.sh): sets `PYTHONPATH` so the package runs without install.
- [REPO_TYPE](../REPO_TYPE): project-type marker used by shared tooling.

## Key subtrees

### qti_package_maker (the package)
```text
qti_package_maker/
+- package_interface.py     public QTIPackageInterface orchestration API
+- assessment_items/        the item bank hub
|  +- item_bank.py          ItemBank container + media asset collection
|  +- item_types.py         question type classes (MC, MA, MATCH, NUM, ...)
|  `- validator.py          item content and HTML validation
+- engines/                 reader/writer engines (the plug-in edges)
|  +- base_engine.py        BaseEngine contract + shared render loop
|  +- engine_registration.py  dynamic engine discovery and registry
|  +- canvas_qti_v1_2/      one folder per engine (engine_class + write/read)
|  +- blackboard_qti_v2_1/
|  +- blackboard_export_zip/
|  +- template_class/       copy-me starter (skipped by registration)
|  `- ...                   more engines; see docs/ENGINES.md
+- common/                  shared layers used by both readers and writers
|  +- media_assets.py       image scan / classify / name / rewrite / policy
|  +- zip_writer.py         deterministic ZIP builder for packaging engines
|  +- qti_manifest.py       imsmanifest.xml generation (incl. image webcontent)
|  +- string_functions.py   text helpers
|  +- color_theory/         color-wheel question support
|  `- ...                   anti_cheat, yaml_tools, tabulate_compat, ...
`- data/                    packaged runtime data (all_short_words.txt)
```

### tests
- [tests/unit](../tests/unit): fast unit tests for individual modules, including the
  media units (for example
  [tests/unit/test_media_assets.py](../tests/unit/test_media_assets.py) and
  [tests/unit/test_item_bank_media.py](../tests/unit/test_item_bank_media.py)).
- [tests/integration](../tests/integration): whole-engine and round-trip coverage,
  including media end-to-end and reader/writer round trips.
- [tests/fixtures/bb_export_slice.zip](../tests/fixtures/bb_export_slice.zip): a
  trimmed, real-shape Blackboard export slice zipped into a single 12K archive with
  `imsmanifest.xml` at its root, the one committed durable media fixture; its
  [tests/fixtures/bb_export_slice_README.md](../tests/fixtures/bb_export_slice_README.md)
  explains what was kept.
- Top-level `tests/test_*.py` files are repo-wide gates (pyflakes, ASCII compliance,
  typing, imports, shebangs, markdown links) plus the all-engines smoke run.
- `tests/e2e/` and `tests/playwright/` hold slow end-to-end scripts run outside
  pytest; see [E2E_TESTS.md](E2E_TESTS.md).

### devel
- The `build_*_probe.py` scripts
  ([devel/build_canvas_media_probe.py](../devel/build_canvas_media_probe.py),
  [devel/build_bb_original_probe.py](../devel/build_bb_original_probe.py),
  [devel/build_ultra_media_probe.py](../devel/build_ultra_media_probe.py)) build small
  QTI packages a human can import into a real LMS to confirm which image-reference
  variant each platform accepts; results are recorded in
  [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md).

## Generated artifacts
- Ignored outputs include `output*/` directories and generated `*.html`, `*.zip`, and
  `*.xml` files, plus `report_*.txt` and the `ULTRA/` scratch dir; see
  [.gitignore](../.gitignore).
- Root-level `BB-Export-*` folders and `SAMPLES/` are local sample exports, not part of
  the tracked package.

## Documentation map
- All documentation lives under [docs](.); root-level docs are
  [README.md](../README.md) and [AGENTS.md](../AGENTS.md).
- Architecture and layout: this file and
  [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md).
- Formats and engines: [FORMATS.md](FORMATS.md), [ENGINES.md](ENGINES.md),
  [ENGINE_AUTHORING.md](ENGINE_AUTHORING.md),
  [QUESTION_TYPES.md](QUESTION_TYPES.md).
- Install and run: [INSTALL.md](INSTALL.md), [USAGE.md](USAGE.md).
- Media specifics: [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md).

## Where to add work
- New format or LMS target: a new engine folder under
  [engines](../qti_package_maker/engines).
- New question type or validation rule:
  [assessment_items](../qti_package_maker/assessment_items).
- Behavior shared across engines: [common](../qti_package_maker/common).
- New command-line tool: [tools](../tools).
- Tests: [tests/unit](../tests/unit) or [tests/integration](../tests/integration).
- Documentation: [docs](.).
