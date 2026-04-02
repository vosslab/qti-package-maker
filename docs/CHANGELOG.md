# Changelog

## 2026-04-02

### Additions and New Features
- Add `exam_yaml` write-only engine that exports an ItemBank to exam YAML format for printable ODT exam generation. Supports MC, MA, MATCH, ORDER, NUM, FIB, and MULTI_FIB item types. This is an intentionally lossy export: answer keys, scoring metadata, and section structure are not preserved. Inline HTML tags (`<sub>`, `<sup>`, `<b>`, `<strong>`, `<i>`, `<em>`) and HTML entities (`&Delta;`, `&deg;`, etc.) are passed through verbatim.

## 2026-04-01

### Additions and New Features
- Add `_detect_tablefmt()` and `_has_visible_border()` helpers in `string_functions.py` that inspect HTML table border attributes to choose the appropriate tabulate format: `"fancy_grid"` for cell-level visible borders, `"plain"` for `border="0"`, and `"fancy_outline"` for table-level border with collapse.
- Add four unit tests for border-aware tablefmt detection: visible cell borders, cell `border: 0` (metabolic pathway pattern), `border="0"` attribute, and border-collapse.

### Fixes and Maintenance
- Fix `_html_table_to_text()` rendering borderless HTML tables (e.g., metabolic pathway diagrams) with box-drawing grid lines. Tables with `border: 0` on cells now correctly use plain format instead of `fancy_grid`.

### Decisions and Failures
- Reviewed all `tablefmt` calls across the codebase (5 call sites). Console display calls in `item_bank.py` and `engine_registration.py` all use `"fancy_outline"` consistently. No consolidation needed; adding a shared constant would add indirection without benefit.

## 2026-03-30

### Behavior or Interface Changes
- Rename changelog section headings to match REPO_STYLE.md spec: `Added` to `Additions and New Features`, `Changed` to `Behavior or Interface Changes`, `Fixed` to `Fixes and Maintenance`, `Removed` to `Removals and Deprecations`, `Chore` to `Fixes and Maintenance`.
- Replace backslash-escaped quotes with alternating quote styles in `html_functions.py`.
- Add return type hints to public functions in `item_types.py`, `item_bank.py`, `string_functions.py`, and `html_functions.py`.
- Refactor `from`/`as` imports to direct module imports in `test_multi_engine_roundtrip.py` and `test_html_selftest_output.py`.
- Convert 3-space indentation to tabs in `rcp_debug_plots.py`.
- Bump version from 26.02 to 26.03.
- Fix version mismatch check in `bbq_converter.py` to normalize PEP 440 versions before comparing (e.g., `26.03` vs `26.3`); use `packaging.version.Version` for proper normalization.
- Add editable-install sync check to `devel/submit_to_pypi.py` that detects stale `pip install -e .` metadata before running pytest, preventing confusing version mismatch failures.
- Add bold choice letters (A., B., C., etc.) to html_selftest MC and MA labels.
- Wrap html_selftest choice text in a `<span>` so `<sub>` and `<sup>` tags render as proper subscripts and superscripts inside flex labels.
- Add visible-text-length check to `determine_choice_layout_class()` so choices longer than 50 visible characters force vertical layout instead of grid.
- Strip HTML tags and unescape entities before measuring choice text length for layout decisions.
- Remove `__version__` assignment from `qti_package_maker/__init__.py`; version check in `bbq_converter.py` now uses `importlib.metadata.version()` directly.
- Remove re-exports and `__all__` from `color_theory/__init__.py`; all consumers already import submodules directly.
- Rename `color_theory/main.py` to `color_theory/rcp_debug_plots.py` to reflect its role as a dev visualization script.
- Move `matplotlib`, `numpy`, and `scipy` from `pip_requirements.txt` to `pip_requirements-dev.txt` (only used in `rcp_debug_plots.py`).
- Remove incorrect `colour` entry from `pip_requirements.txt`; add `"colour": "colour-science"` alias to `test_import_requirements.py`.

## 2026-02-07

### Additions and New Features
- Add temporary root note `TEMP_RDKit_QTI_IMPORT_NOTES.md` summarizing observed RDKit/script import behavior across Canvas QTI 1.2, Blackboard QTI 2.1, Blackboard BBQ text, and ADAPT QTI 1.2.

## 2026-02-06

### Behavior or Interface Changes
- Add extra blank-line spacing between major XML sections in Canvas QTI v1.2 and Blackboard QTI v2.1 outputs to improve manual readability.
- Add unit assertions for QTI spacing patterns and reinforce BBQ text upload single-line output behavior.

## 2026-02-05

### Additions and New Features
- Add Agent Self-Check Questions section to AGENTS.md with key questions agents should answer after reading repository guidelines.
- Add unit tests for adaptive grid layout: test_determine_choice_layout_class, test_html_selftest_mc_adaptive_grid_classes, test_html_selftest_ma_adaptive_grid_classes.

### Behavior or Interface Changes
- Add adaptive CSS Grid layouts for html_selftest MC/MA choices based on choice count.
- Use CSS Grid auto-fit with minmax to automatically arrange choices based on rendered width.
- Apply compact grid (min 150px columns) for 4-5 choices, standard grid (min 200px) for 6+ choices.
- Keep vertical layout for 2-3 choices for optimal readability.

## 2026-02-03

### Behavior or Interface Changes
- Align html_selftest MC/MA choice inputs and labels with flex layout styling.
- Increase html_selftest input font size and apply theme input styling to FIB inputs.

## 2026-02-02

### Additions and New Features
- Add tests/test_strip_prefix.py to guard decimal handling in prefix stripping helpers.
- Expand decimal cases in tests/test_strip_prefix.py for numeric prefixes like 0.0089 and 12.5.

### Behavior or Interface Changes
- Restrict prefix dot matching to non-decimal cases to preserve numeric answers.
- Fix YY.MM regex parsing in devel/bump_version.py for short prerelease versions.
- Allow bare YY.MM versions in bump_version validation.
- Treat YY.MM and YY.MM prerelease strings as version candidates in bump_version scanning.
- Force VERSION file updates even when the existing value is not a recognized version.
- Allow --update-all --set-version to proceed when multiple versions are discovered.
- Skip pip upgrades in devel/submit_to_pypi.py to avoid Homebrew-managed pip failures.

## 2026-01-19

### Behavior or Interface Changes
- Replace yaml.load usage with a safe loader path that preserves duplicate key checks.
- Update unit tests to use pytest tmp_path instead of hardcoded /tmp paths for Bandit compliance.
- Escape non-ISO-8859-1 characters in html_selftest HTML output with numeric entities.
- Add tests dir to sys.path in pytest conftest to allow local test imports.
- Use git rev-parse to determine REPO_ROOT in pytest conftest.
- Scope html_selftest MATCH drag-and-drop initialization by item id to avoid multi-item collisions.
- Scope html_selftest MATCH/ORDER dropzone queries to each item container and add output tests for scoping.
- Use append_const for bbq_converter format shortcuts so flags like -s do not suggest an argument.

## 2026-01-16

### Behavior or Interface Changes
- Refresh README.md to a concise overview with a quick start and curated documentation links.
- Refresh docs/INSTALL.md and docs/USAGE.md to minimal, evidence-based stubs.
- Add docs/CODE_ARCHITECTURE.md and docs/FILE_STRUCTURE.md and link them from README.md.
- Prune README.md documentation links to the required core set plus a short "More docs" list.
- Remove shebangs from non-executable color_theory modules to satisfy shebang_not_executable lint.
- Fix mixed-indentation lines in item_types, anti_cheat, and text2qti read_package.
- Remove invalid python shebangs from non-executable modules flagged by lint.
- Remove shebangs from pytest modules flagged as non-executable.
- Remove shebangs from additional non-executable engine/test modules flagged by lint.
- Remove remaining non-executable shebangs from unit tests to satisfy shebang alignment checks.

## 2026-01-15

### Behavior or Interface Changes
- Simplify `color_wheel.py` public API to single function `generate_color_wheel()`.
- Switch default color wheel backend from legacy to CAM16.
- Restore public color wheel shims for named wheels and legacy helpers, backed by CAM16 output.
- Remove unused imports from `next_gen.py` and `generator.py`.
- Update color wheel tests to import internal functions directly from source modules.
- Fix bugs in `main.py`: typo in `_validate_hsl` error message, undefined `l` variable, remove dead `sys.exit()` call.
- Remove unused `pytest` imports from test files.

### Fixes and Maintenance
- Resolve all 46 pyflakes errors (reduced to 0).

## 2026-01-14

### Behavior or Interface Changes
- Replace Unicode box-drawing and emoji in `docs/CODE_DESIGN.md` with ASCII equivalents.
- Replace checkmark/cross table markers with yes/X in `docs/ENGINES.md`.
- Replace Unicode status symbols in test output strings and use ASCII-safe escapes for sub/superscript mappings.

## 2026-01-13

### Behavior or Interface Changes
- Resolve README merge markers and restore the question types/engine sections.
- Make README ISO-8859-1 compatible by replacing non-ASCII table symbols.
- Fix README formatting in the Python API example block.

## 2026-01-03

### Additions and New Features
- **Planning**: Add `COLOR_WHEEL_REFACTOR_PLAN.md` with a perceptual color sampling plan and visual test notes.
- **Next-gen experiments**: Add `qti_package_maker/common/color_wheel_next_gen.py` for OKLCH-based color wheel experiments.
- **Tests**: Add pytest coverage for next-gen color wheel utilities.

### Behavior or Interface Changes
- **Refactor plan & docs**: refine hue spacing and fixed lightness bands; define even chroma via shared min max chroma; add working history; add design corrections and per-wheel policy guidance; add/remove xdark/normal policy drafts per scope; replace plan with CAM16-based plan and rollout steps; add dependency notes; keep CAM16 opt-in until default; add Remaining Items.
- **Module structure & compatibility**: move color wheel modules into `color_wheel/` with shims; expand shim exports for tests; remove OKLCH next-gen module/tests while keeping legacy in `legacy_color_wheel.py`; add deprecation warning and update tests to import legacy directly; move implementations to `color_theory/` with legacy facade; add `generate_color_wheel` facade; add legacy parity + CAM16 smoke tests.
- **CAM16 implementation & tuning**: select `colour-science` and wire CAM16 adapter/skeleton; adjust J targets (add very_dark, lighten dark/light, xdark/normal tweaks); boost dark saturation and soften light/pastel output; rotate wheels so hue 1 anchors to true red; emit legacy red RGB distance in HTML; use American spelling (except `colour-science`).
- **Debug & inspection tooling**: add CAM16 debug HTML; anchor to best-red offsets; make deterministic; add XKCD name labels; add CAM16-UCS radius/gamut margin/per-hue max-M utilization; remove M/gamut_limit from debug; add UCS target diagnostics; add control selection indicator; add clamp_reason and prefer per-hue M_max caps for UCS control; add CAM16 spec helper and J/M/Q range tests.
- **Light UCS control**: remove mode-level M caps for UCS-driven modes and skip max-M anchoring in debug/HTML for UCS modes.
- **Validation**: enforce shared_m_quantile in [0.0, 1.0] and add pytest coverage for invalid quantiles.
- **Release tooling**: remove repo-derived CLI args from `devel/submit_to_pypi.py`, require VERSION file, and fix rich stderr output.
- **Release tooling**: test installs now pin the exact version (with --pre when needed) and project URLs use canonicalized names.
- **Release tooling**: always check for existing versions; `--version-check` now runs the check and exits.
- **Release tooling**: remove clean/upgrade/test-install/open toggles and index/repo URL overrides; these steps now run unconditionally.
- **Release tooling**: add pre-checks (PEP 440 version parse, requires-python, git clean/main, version tag, twine, pytest when installed, and dist empty after clean).
- **Release tooling**: require `main` to be fully synced with `origin/main` (fetch + ahead/behind check).
- **Release tooling**: add `--build-only` mode and log build output to `build_output.log`.
- **Release tooling**: add index reachability check before version lookup.
- **Release tooling**: include prereleases when checking index versions.
- **Release tooling**: normalize version strings for index checks and test installs (e.g., 26.01rc2 -> 26.1rc2).
- **Release tooling**: retry test install when the new version is not indexed yet.
- **Release tooling**: link to the version-specific project page by default.
- **Release tooling**: add `--set-version` to bump VERSION/pyproject, commit, tag, and push.
- **Versioning**: bump VERSION/pyproject to 26.01rc2.
- **Red anchor & scan tooling**: optimize hue offsets and anchor selection; scan all offsets and choose reddest at max chroma; adjust red scoring (|G-B|/(G+B) + (G+B)/(2R)); add multi-stage best-red search, cache seeding/updates; add --best-red + red-scan HTML (coarse/fine/micro), bundle all modes, 0.2 micro step; switch CLI to argparse/named args and remove --scan-mode; treat red offsets as global per mode.
- **YAML-driven config**: add `wheel_specs.yaml` and load defaults in `wheel_specs.py`; load modes/offsets from YAML across tools; simplify YAML to per-mode `target_j`/`red_offset`; add pytest coverage for YAML mode order and offsets; enforce XOR between `shared_m_quantile` and `target_ucs_r`.
- **YAML-driven config**: remove hardcoded mode names from tests and HTML defaults; use YAML mode order everywhere.
- **Versioning**: sync `pyproject.toml` and root `VERSION` to 26.01rc1.
- **Debug & inspection tooling**: label legacy red distance output with the actual YAML mode names used.
- **HTML output**: prefer `dark`/`light`/`xlight` modes by name (when present) for the legacy-style color table columns.
- **HTML output**: require `dark`/`light`/`xlight` in YAML for the legacy table; error if missing.
- **Color name matching & deps**: add `rgb_color_name_match` using seaborn xkcd; add `seaborn` dependency; remove `webcolors`; remove `rcp-color-utils.py`.
- **Testing & engine work**: move module-level asserts into pytest; expand pytest coverage for writers/manifest/helpers/round-trips/validators/xml formatter/yaml tools/string helpers/color wheel; add round-trip coverage across BBQ/text2qti/okla_chrst_bqgen; add QTI ZIP/manifest tests and error-path coverage; fix engine selection ambiguity, item bank merge type tracking, BBQ NUM zero-division handling; update TODO/ROADMAP, mark Canvas QTI 1.2 ORDER as won't implement, expand ROADMAP priorities, and preserve legacy TODO/ROADMAP content.

## 2025-12-29

### Additions and New Features
- Add [docs/TEST_PLAN.md](TEST_PLAN.md) with pytest suite ideas before implementation.
- Add pytest unit and integration coverage for item types, validators, engines, and CLI.
- Add pytest fixtures in `tests/conftest.py` for shared sample items and temp cwd.
- Add integration output checks for QTI ZIPs, human readable, BBQ, and HTML outputs.
- Add pytest unit coverage for text2qti and okla_chrst_bqgen reader parsing.
- Add reader/writer roundtrip smoke tests for BBQ, text2qti, and okla_chrst_bqgen engines.
- Add edge-case tests for text2qti and BBQ reader error paths plus okla unknown-block handling.
- Add unit coverage for missing NUM tolerances in BBQ/text2qti readers.
- Add unit coverage for NUM writers with zero tolerance.
- Add unit coverage for engine registry, manifest generation, YAML helpers, and anti-cheat.
- Add [docs/ENGINE_AUTHORING.md](ENGINE_AUTHORING.md) with engine authoring guidance.
- Add internal engine cleanup notes in `qti_package_maker/engines/ENGINE_CLEANUP.txt`.
- Add docs consistency check to keep engine names in sync with the registry.
- Add unit coverage for BaseEngine filename helpers and histogram output.
- Add CLI error-path coverage for invalid BBQ filenames.
- Add manifest schema metadata checks for QTI v1.2 and v2.1 outputs.
- Add engine class contract smoke tests (imports and write_item wiring).
- Add ZIP safety checks to prevent absolute or parent directory paths.
- Add BBQ parsing error-path coverage for missing correct flags.
- Add BaseItem repr smoke test.

### Behavior or Interface Changes
- Convert script-based tests into pytest functions using fixtures and tmp paths.
- Register pytest `smoke` marker and fix item type test inputs.
- Add format_html_lxml and anti-cheat edge case tests.
- Adjust BaseEngine test harness and anti-cheat expectations for current behavior.
- Use ItemBank.add_item_cls for okla_chrst_bqgen reader to preserve question text.
- Default BBQ NUM tolerance to 0.0 with a warning when the field is missing.
- Fix text2qti MA detection for `[ ]` choices and raise clearer errors for missing NUM/FIB answers.
- Emit explicit tolerance in text2qti NUM writer output (including 0.0).
- Limit BBQ and text2qti read skipping to parse-time ValueError/IndexError.
- Refine engine authoring guidance with overview, discovery command, and ZIP tip.
- Expand engine authoring guidance with examples, mapping table, and troubleshooting.
- Add engine authoring tables for interfaces, artifacts, tests, and failure modes.
- Align engine authoring examples with EngineClass patterns and testing guidance.
- Clarify recommended pytest targets and what they cover for engine authors.
- Rewrite engine docstrings for accuracy and consistency across engine modules.
- Note MkDocs Material light/dark theming for html_selftest in TODO and roadmap.
- Reference MkDocs Material palette tokens in html_selftest theming docs.
- Record engine cleanup completion notes for randomness helper and allow_mixed plumbing.
- Rename random item helper in BaseEngine and update tests.
- Add scoped html_selftest theme injection and palette-aware colors for matching/ordering.
- Document CRC-suffixed JavaScript function naming in html_selftest helpers.
- Use html_selftest theme variables for dropzone borders and reset colors.
- Mark html_selftest MkDocs palette theming as done in TODO/ROADMAP.
- Add html_selftest output validation tests for HTML parsing and theme markers.
- Add html_selftest HTML validator that tolerates JavaScript blocks.
- Update engine docs for html_selftest FIB support and remove stale TODO entry.

## 2025-12-20

### Additions and New Features
- Add `docs/DEVELOPMENT.md` with setup, testing, and engine guidance.
- Add `docs/FORMATS.md` with input/output format notes and engine list.
- Add `docs/TROUBLESHOOTING.md` with common issues and fixes.
- Add `docs/INSTALL.md`, `docs/USAGE.md`, `docs/QUESTION_TYPES.md`, and
  `docs/ENGINES.md` to split README content into focused guides.
- Add `docs/RELATED_PROJECTS.md` and `docs/COMMUNITY.md` to move link lists and
  support info out of README.
- Add `TODO.md` to track feature ideas and missing item implementations, migrated from
  `TODO.txt`.
- Add `ROADMAP.md` to capture longer-form plans such as hints support.
- Add feedback planning section to `ROADMAP.md`.

### Behavior or Interface Changes
- Update `README.md` with documentation links and a backlog pointer.
- Update `TODO.md` to point hint planning at `ROADMAP.md`.
- Move documentation files (changelog, roadmap, todo, style guides, and legacy docs)
  into `docs/` to reduce root-level clutter.
- Split `README.md` into shorter sections with links to new docs.
- Rename `docs/INSTALLATION.md` to `docs/INSTALL.md` and
  `docs/DEVELOPER.md` to `docs/DEVELOPMENT.md`.

### Removals and Deprecations
- Remove legacy `docs/TODO.txt` and `docs/old_README.md` in favor of updated docs.

## 2025-12-12

### Additions and New Features
- Add `qti_package_maker/common/tabulate_compat.py` with a fallback plain-text table renderer.
- Add HTML `<table>` to plain-text conversion in `qti_package_maker/common/string_functions.py`.

### Behavior or Interface Changes
- Use `tabulate_compat` in `qti_package_maker/assessment_items/item_bank.py` and
  `qti_package_maker/engines/engine_registration.py`.
- Pass `allow_mixed` through `qti_package_maker/package_interface.py` when supported, and
  forward it in `qti_package_maker/engines/text2qti/engine_class.py` and
  `qti_package_maker/engines/bbq_text_upload/engine_class.py`.
- Allow table markup in `qti_package_maker/engines/human_readable/write_item.py` content checks.

### Removals and Deprecations
- Remove unused variables in `qti_package_maker/engines/text2qti/write_item.py`.
- Remove unnecessary `global` declarations in `qti_package_maker/common/franken_bptools.py`.

### Fixes and Maintenance
- Ignore `pyflakes.txt` in `.gitignore`.
- Mark tests executable: `tests/test_bbq_converter_all_types.py` and
  `tests/test_human_readable_tables.py`.
