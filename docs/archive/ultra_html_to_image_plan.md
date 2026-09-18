# Plan: Convert Blackboard Ultra-incompatible HTML into images

Replaces `floating-wiggling-castle.md` (2026-08-03). On approval this text overwrites that file and
is mirrored to `docs/active_plans/active/ultra_html_to_image_plan.md`.

## Context

Blackboard Ultra strips every `style=`, `class=`, and presentational attribute on import
(`docs/BLACKBOARD_ULTRA_NOTES.md`). Two content families in the sibling `biology-problems` repo
lose their meaning as a result:

- **Table-cell drawings.** Generators use `<td>` cells as drawing primitives, relying on exactly
  the attributes Ultra strips (`style`, `bgcolor`, `border`, `cellspacing`, `align`). The user's
  test set for this work (all under `biology-problems/problems/`):
  - `dna_profiling-problems/who_father_html.py` and `who_killer_html.py` -- DNA gels via
    `gellib.py`: lanes are `<td style="border-top: 1px solid <color>">` bands with `bgcolor`.
  - `dna_profiling-problems/blood_type_agglutination_test.py` -- agglutination wells:
    `<td style="border: 2px solid gray">` result cells, `border: 0px solid white` spacer cells,
    `cellspacing="150"`, and `<span style="font-size: ..px; color: ...">` symbols.
  - `molecular_biology-problems/restriction_enzymes/linear_digest.py` -- fragment maps:
    `<td style="border: ..." bgcolor="...">` with `colspan`.
  Further families found by search and used as secondary fixtures: Fischer/Haworth projections
  (`biochemistry-problems/carbs/sugarlib.py`, `padding: 0` cells), pedigrees, fraction bars, and
  binomial layouts (`inheritance-problems/`). None of the test-set generators uses `padding: 0`,
  so the earlier plan's selector hypothesis is already falsified by the test set. Ultra drops the
  styles and every one of these drawings collapses into a run of characters.
- **RDKit JavaScript canvases.** `problems/biochemistry-problems/PUBCHEM/moleculelib.py` (6
  consumers) emits `<canvas id="canvas_<crc>" width height>` plus a `<script>` that loads
  `https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js` and draws from a SMILES literal
  (`let/* */smiles="..."`). Outside debug mode the only drawing options are
  `mdetails["legend"]` (molecule name, when it has no spaces) and
  `mdetails["explicitMethyl"]=true` (`moleculelib.py:62-73`). JavaScript stays inert after QTI
  import (`docs/active_plans/audits/rdkit_qti_import_notes.md`); the learner sees an empty box.

Everything needed to SHIP an image already exists and is verified: gate D PASS (2026-07-02) proved
`<img>` PNGs render in Ultra through `blackboard_qti_v2_1` and `blackboard_export_zip`; the media
layer (`common/media_assets.py`, `common/zip_writer.py`, `ItemBank.add_image / collect_assets /
set_media_base_dir / cleanup`) packages any local image. The single missing piece is local image
GENERATION from the offending HTML. The 2026-08-03 plan chose a pure-Pillow redraw with a
reviewer-scored readability rubric across eight milestones; none of it was started. The user has
since chosen the Playwright hybrid and asked for a KISS plan with many small milestones and no
human gates.

Environment evidence (2026-09-18): Python `playwright 1.57.0`, `rdkit 2026.3.5`, and
`pillow 12.3.0` are installed in `/opt/homebrew/lib/python3.12/site-packages/`; Playwright's
Chromium is cached under `~/Library/Caches/ms-playwright/`. `biology-problems/pip_requirements.txt`
already requires `rdkit`. This repo has no `package.json`; Playwright here is the pip package.
`devel/setup_playwright.sh` is a stale npm template from the starter repo and is unused.

## Objectives

- A bank whose items contain table-cell drawings or RDKit canvases converts, on request, into a
  bank whose items carry `<img src alt>` references to generated PNGs the media layer packages.
- Every other fragment passes through as authored.
- The feature is off by default; with it off, packaged item HTML is the input HTML.
- Every milestone completes on checks a manager and subagents run alone.

## Design philosophy

**Perfect is the enemy of good** and **fix the design, not the symptom** (`docs/REPO_STYLE.md`).
A headless browser renders these fragments the way Blackboard Learn Classic did, so the table
renderer is a screenshot, not a layout engine. The 2026-08-03 plan's Pillow redraw and readability
rubric solved a problem the browser makes moot; they are dropped.

Trade-off accepted: Playwright needs a one-time `playwright install chromium` after `pip install`.
The user chose this over the pure-pip constraint. Rejected alternative: WeasyPrint (needs brew
pango/cairo, no JavaScript, PNG via PDF rasterization -- more moving parts than a browser).

The canvas family is drawn by RDKit's Python API from the embedded SMILES rather than by the
browser, because the browser path fetches `RDKit_minimal.js` from unpkg at render time and an
offline run would produce an empty canvas. RDKit Python is installed, deterministic, and offline,
and the generator's two drawing options (`legend`, `explicitMethyl`) both have direct
`MolDrawOptions` equivalents, so the redraw carries the same information.

The screenshot is faithful because the source diagrams depend only on their own inline styles:
`sugarlib.py` sets every border, padding, alignment, and font-size inline and references no
stylesheet, class, or font family (verified by search). The wrapper document supplies only a white
background, a margin, and the browser's default sans-serif font, and leaves every inline style as
authored.

Selection is two hard-coded selectors held in a list of `(selector, renderer)` pairs. The list is
the seam: a third fragment type is one appended pair (**design for adaptability**), and the
transform, engines, and CLI stay as they are.

- Evidence strategy for uncertain methods: the table selector rule and the screenshot wrapper are
  hypotheses tested against captured fixtures. A `reviewer` subagent reads each rendered PNG (the
  Read tool renders images) and answers a three-item checklist. A failure means the source pattern
  is not yet understood: the manager records it under `docs/CHANGELOG.md` "Decisions and
  Failures", adjusts the wrapper or selector once, and re-renders. A second failure on the same
  fixture blocks release of that family until the plan is revised with the new evidence, because
  the feature exists to preserve exactly that meaning.

## Scope

- Capture representative HTML fixtures from both families as inline string constants.
- Build `qti_package_maker/html_to_image/` with selectors, a Playwright table renderer, an RDKit
  canvas renderer, and an `ItemBank -> ItemBank` transform.
- Add an opt-in `html_to_image: bool = False` constructor keyword to `blackboard_export_zip` and
  `blackboard_qti_v2_1`, applied before each engine's `collect_assets()` call.
- Pass engine constructor options through `QTIPackageInterface.save_package()` and add one
  `tools/bbq_converter.py` flag.
- Declare `playwright` and `rdkit` in `pip_requirements.txt` and `pyproject.toml`; document the
  Chromium install step in `docs/INSTALL.md`.
- Add the permanent tests that protect the contract, one E2E evidence runner, and docs.

## Non-goals

- Keep the screenshot as the fidelity standard; Ultra's and Classic's exact pixels stay out.
- Keep the canvas renderer on RDKit Python; the browser draws tables only.
- Keep selection as the list of pairs; registry, priority rules, and author markers wait for a
  demonstrated third fragment type.
- Keep `BaseItem`, the `ItemBank` public API, and every `biology-problems` file as they are.
- Keep `moodle_aiken` and `human_readable` declining RDKit items; revisit after release.
- Keep audio and video for a later plan.

## Current state summary

- `ItemBank.add_image(src, data_bytes) -> str` (`assessment_items/item_bank.py:309`) spills bytes
  under `media_base_dir`, creating and OWNING a temp dir when none is set; `cleanup()` (`:380`)
  removes only owned dirs. `collect_assets()` (`:400`) resolves `<img src>` per item.
- `blackboard_export_zip.save_package()` (`engines/blackboard_export_zip/engine_class.py:142`)
  runs `_plan_image_embedding()` (validation, may raise) BEFORE creating the staging dir at `:146`,
  and removes the staging dir at `:222` after zipping. There is no try/except (repo rule); a
  mid-write exception leaves the staging dir, which is the existing behavior. `blackboard_qti_v2_1`
  collects at `engine_class.py:103`.
- `canvas_qti_v1_2.engine_class.__init__` (`:56-75`) is the precedent for a validated constructor
  keyword that is also a settable attribute; today only `devel/build_canvas_media_probe.py` sets
  it, by constructing the engine directly. `QTIPackageInterface.init_engine()`
  (`package_interface.py:66`) constructs engines as `cls(package_name, verbose)` with no option
  pass-through, so no engine option is reachable from `tools/bbq_converter.py`.
- `media_assets.rewrite_item_media()` deep-copies an item before rewriting -- the established
  "render from a copy" pattern.
- `common/string_functions._html_table_to_text()` (`:83`) converts a table to text via tabulate;
  the alt-text source for tables.
- `common/package_integrity.check_package()` validates a finished package's manifest, media, and
  cross-links; the integration oracle.
- `tests/conftest.py` excludes `e2e` and `playwright` from pytest; `tests/e2e/` does not exist yet.
  `tests/_temp/` is the documented home for temporary checks (`docs/PYTHON_STYLE.md`).
- `docs/ROADMAP.md:49` still lists rasterization as out of scope; stale.

## Architecture boundaries and ownership

New package `qti_package_maker/html_to_image/`:

- `selectors.py` -- `find_table_fragments(html) -> list` and `find_canvas_fragments(html) ->
  list[CanvasSource]`. Table rule (hypothesis, M2 tests it against the test-set positives, the
  secondary positives, and two negatives): a `<table>` is selected when any descendant `td`/`th`
  carries a `bgcolor` attribute, or a `style` containing `border`, `background`, or exact
  `padding: 0` -- the attributes Ultra strips that carry visual meaning in a drawing. A data
  table whose cells carry no style, or only `text-align`, is left alone.
  Canvas rule: a `<canvas>` whose following `<script>` sibling contains `RDKitModule`; the record
  carries `smiles`, `legend` (present or `None`), `explicit_methyl`, width, height, and both
  elements so the transform removes them together.
- `render_table.py` -- `render_table_png(table_html: str) -> bytes`. Wraps the fragment in
  `<html><body style="margin:16px;background:#fff;font-family:sans-serif">`, opens headless
  Chromium via `playwright.sync_api`, and screenshots the `<table>` element at
  `device_scale_factor=2`. A `TableRenderer` context manager holds one browser for the whole
  transform; `render_table_png` is its method.
- `render_canvas.py` -- `render_canvas_png(source: CanvasSource) -> bytes` via
  `rdkit.Chem.Draw.MolDraw2DCairo` at the source's width and height, `legend` from the source,
  `MolDrawOptions.explicitMethyl` from the source.
- `transform.py` -- `convert_bank(item_bank, renderers=DEFAULT_RENDERERS) -> ItemBank`. Phase 1
  renders every selected fragment in every item into memory (no filesystem effect; a rendering
  error raises before anything is created). Phase 2 deep-copies the bank, calls
  `new_bank.add_image(name, png_bytes)` for each rendered fragment, and replaces the fragment with
  `<img src="<name>" alt="<alt>">`. Names are `<item crc16>_<family>_<n>.png`. Alt text: table ->
  `_html_table_to_text()` collapsed to one line; canvas -> `"<legend> (SMILES <smiles>)"` or
  `"SMILES <smiles>"`. The input bank is untouched. The derived bank OWNS its media dir. The
  `renderers` parameter lets unit tests inject a stub and stay under one second without a browser
  (demonstrated need: the pytest time budget).

Engine lifecycle (owner: the engine that converts). In `save_package()`, immediately after the
existing validation step and before the staging dir is created:
`if self.html_to_image: item_bank = transform.convert_bank(item_bank, self.html_to_image_renderers)`.
After the ZIP is written and the staging dir removed: `item_bank.cleanup()` when a conversion
happened. Ordering matches the engine's validation-first rule: rendering failures raise before any
directory exists; failures after conversion leave the derived media dir the same way they leave the
staging dir today. `blackboard_qti_v2_1` follows the same shape around its `collect_assets()` call.

Interface: `QTIPackageInterface.save_package(engine_name, outfile=None, engine_options=None)`;
`init_engine(name, engine_options=None)` passes `**engine_options` to the engine class. This is
the constructor-keyword precedent made reachable from the interface; `canvas_src_variant` is the
second existing user. An engine lacking a keyword raises `TypeError` (fail loud).

CLI: `tools/bbq_converter.py --html-to-image` (store_true, default off) forwarded as
`engine_options={"html_to_image": True}`.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Review boundary |
| --- | --- | --- |
| M1 / WS-FIXTURES | `tests/_temp/` capture script, inline fixture constants | Read-only against sibling repo |
| M2 / WS-SELECT | `html_to_image/selectors.py` | Pure functions over HTML strings |
| M3 / WS-TABLE | `html_to_image/render_table.py` | Playwright only; no bank or engine imports |
| M4 / WS-CANVAS | `html_to_image/render_canvas.py` | RDKit only; no bank or engine imports |
| M5 / WS-TRANSFORM | `html_to_image/transform.py` | New bank returned; input unchanged |
| M6 / WS-ENGINE-BBX | `engines/blackboard_export_zip/engine_class.py` | Switch-off item HTML verbatim |
| M7 / WS-ENGINE-Q21 | `engines/blackboard_qti_v2_1/engine_class.py` | Switch-off item HTML verbatim |
| M8 / WS-CLI | `package_interface.py`, `tools/bbq_converter.py` | Flag absent keeps today |
| M9 / WS-E2E | `tests/e2e/e2e_html_to_image.py`, reviewer readability check | Evidence artifacts |
| M10 / WS-DOCS | deps, `docs/*.md`, `VERSION`, `pyproject.toml` | Markdown links test green |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M1 | Fixture capture | Run the 4 test-set generators to BBQ files; capture their table fragments, 1 sugarlib, 2 canvases, 2 negatives inline | Test-set BBQ files and fixtures exist with provenance |
| M2 | Selectors | Table and canvas selectors over fixtures | All positives found, no negatives |
| M3 | Table renderer | Playwright screenshot of a table fragment | Readable PNG from each table fixture |
| M4 | Canvas renderer | RDKit PNG from extracted SMILES + options | Readable PNG from each canvas fixture |
| M5 | Bank transform | `convert_bank()` with stub-renderer tests | New bank has `<img>`, media resolves |
| M6 | Engine: export ZIP | Keyword + call + cleanup in `blackboard_export_zip` | Switch-on passes integrity |
| M7 | Engine: QTI 2.1 | Same in `blackboard_qti_v2_1` | Same, second engine |
| M8 | Interface and CLI | `engine_options` pass-through + `--html-to-image` | CLI produces converted ZIPs |
| M9 | E2E evidence | Runner uses real renderers via the CLI; reviewer checklist | PNGs read correctly |
| M10 | Deps, docs, release | Requirements, INSTALL, ENGINES, ROADMAP, changelog, version | Docs match behavior |

### Milestone: M1 fixture capture

- Depends on: none.
- Deliverables: (a) `tests/_temp/run_test_set.sh` (untracked scratch) that runs the four test-set
  generators from their own directories with a small `-n` count and copies the resulting
  `bbq-*-questions.txt` files into `output_smoke/test_set/`; (b) `tests/_temp/capture_fixtures.py`
  that extracts one `<table>` fragment from each of those four BBQ files, one Fischer projection
  from `sugarlib`, and two molecule canvases from `moleculelib` (one with a legend, one without),
  and prints them; (c) the fragments pasted as string constants into
  `tests/unit/test_html_to_image_selectors.py` plus two negatives (a plain Michaelis-Menten data
  table from the Ultra probe kit, and `metaboliclib.py`'s label table with `padding: 0 2px` and
  no borders). Provenance (generator, function, seed) recorded in `docs/CHANGELOG.md`.
- Done checks: constants ASCII; each of the four test-set BBQ files exists in
  `output_smoke/test_set/`; each canvas positive contains `RDKitModule` and `smiles=`.
- Entry criteria: none. Exit criteria: `pytest tests/test_ascii_compliance.py` green.
- Parallel-plan ready: no (single capture task).

### Milestone: M2 selectors

- Depends on: M1 (fixtures).
- Deliverables: `html_to_image/selectors.py`; `tests/unit/test_html_to_image_selectors.py`
  asserting each positive is found once, each negative yields an empty list, and one canvas
  record's `smiles`, `legend`, `explicit_methyl`, width, height.
- Done checks: tests green; pyflakes and typing gates green. Failure plan: a negative that
  matches means the rule is too broad -- drop `text-align`-only and `padding: 0 2px` cases
  explicitly and record the final rule in the module docstring; a positive that is missed means a
  new drawing attribute -- add it to the rule and record why.
- Parallel-plan ready: no.

### Milestone: M3 table renderer

- Depends on: M1 (fixtures); independent of M2.
- Deliverables: `html_to_image/render_table.py`; `tests/_temp/render_table_check.py` writing each
  table fixture's PNG to `output_smoke/`; a `reviewer` subagent reads the PNGs and answers: (1)
  every character and line legible, (2) left/right and above/below placement matches the source
  HTML, (3) nothing clipped. Result recorded in the changelog.
- Done checks: each PNG starts with the PNG magic bytes and is larger than 100 px on both axes;
  reviewer yes on all three for every fixture. Failure plan: adjust wrapper body style or scale
  factor once and re-render; a second failure blocks the table family and triggers plan revision.
- Parallel-plan ready: yes -- WS-TABLE (M3) and WS-CANVAS (M4) are independent lanes, max 2.

### Milestone: M4 canvas renderer

- Depends on: M1 (fixtures); independent of M2 and M3.
- Deliverables: `html_to_image/render_canvas.py`; `tests/unit/test_html_to_image_canvas.py` with
  one test: `CanvasSource(smiles="CC(N)C(=O)O", legend="alanine", explicit_methyl=True, 256,
  256)` renders to bytes starting with the PNG magic. Reviewer checklist on both canvas fixtures:
  structure legible, legend present when the source has one, methyl groups shown explicitly.
- Done checks: unit test green in under one second; reviewer yes on both fixtures. Failure plan as
  in M3 (one option adjustment, then block and revise).
- Parallel-plan ready: yes (see M3).

### Milestone: M5 bank transform

- Depends on: M2 (selectors); renderers injected as stubs, so M3/M4 need not be done.
- Deliverables: `html_to_image/transform.py`; `tests/unit/test_html_to_image_transform.py` with
  a stub renderer returning fixed PNG bytes: (a) the converted item's text contains one `<img src
  alt>` and no `<table` / `<canvas`; (b) the input bank's item text is unchanged after the call;
  (c) `new_bank.collect_assets()` resolves the image; (d) `new_bank.cleanup()` removes the owned
  dir; (e) a stub renderer that raises leaves no directory behind (phase-1 contract).
- Done checks: tests green; full `pytest tests/` green.
- Parallel-plan ready: no.

### Milestone: M6 engine: blackboard_export_zip

- Depends on: M5 (transform).
- Deliverables: keyword, `html_to_image_renderers` attribute (default `DEFAULT_RENDERERS`), call,
  and cleanup in `save_package()`; `tests/integration/test_html_to_image_packaging.py` case: a
  bank with one table fixture, stub renderer, switch on -> `check_package()` zero violations and
  the ZIP namelist contains one `.png`; switch off -> ZIP namelist contains no `.png` and the
  packaged item HTML contains the original `<table` fragment verbatim.
- Done checks: tests green; `test_staging_dir_leak.py` still green. Failure plan: a switch-off
  difference is a wiring defect and blocks.
- Parallel-plan ready: yes -- M6 and M7 touch disjoint engine dirs, max 2.

### Milestone: M7 engine: blackboard_qti_v2_1

- Depends on: M5. Same deliverables and done checks as M6 for the QTI 2.1 engine, as a second
  case in the same integration test file.
- Parallel-plan ready: yes (see M6).

### Milestone: M8 interface and CLI

- Depends on: M6, M7 (both engines accept the keyword).
- Deliverables: `engine_options` on `QTIPackageInterface.save_package()` and `init_engine()`;
  `--html-to-image` flag in `tools/bbq_converter.py`. Verified by the M9 runner (whole-system),
  not by a new pytest.
- Done checks: `pytest tests/` green; running the CLI without the flag produces the same file set
  as before.
- Parallel-plan ready: no.

### Milestone: M9 E2E evidence

- Depends on: M3, M4, M8.
- Deliverables: `tests/e2e/e2e_html_to_image.py` -- writes a BBQ text file from the inline fixtures
  into `output_smoke/`, runs `tools/bbq_converter.py --html-to-image -B -2` on it, runs
  `check_package()` on both ZIPs, and prints PNG names and sizes. Then the same command runs on
  each of the four `output_smoke/test_set/bbq-*.txt` files from M1 (the user's real test set).
  Reviewer subagent reads the PNGs from all ZIPs with the M3/M4 checklist. `tests/_temp/` scratch
  scripts deleted.
- Done checks: runner exits 0; reviewer yes on every fixture. Failure plan as in M3.
- Parallel-plan ready: no.

### Milestone: M10 deps, docs, release

- Depends on: M9.
- Deliverables: `playwright` and `rdkit` in `pip_requirements.txt` and `pyproject.toml`;
  `docs/INSTALL.md` gains `playwright install chromium`; `docs/ENGINES.md` and `docs/USAGE.md`
  document the keyword and flag; `docs/ROADMAP.md:49` updated; `docs/BLACKBOARD_ULTRA_NOTES.md`
  "Deferred" section notes completion; `docs/CHANGELOG.md`; CalVer bump in `VERSION` and
  `pyproject.toml`; `git mv` this plan to `docs/archive/`; delete `devel/setup_playwright.sh`.
- Done checks: `pytest tests/test_markdown_links.py tests/test_import_requirements.py
  tests/unit/test_docs_consistency.py` green; full suite green.
- Parallel-plan ready: no.

## Workstream breakdown

Workstreams map one-to-one to milestones (see Mapping). Owners: `coder` for M1, M2, M5-M8, M10;
`expert_coder` for M3 and M4; `reviewer` for the M3, M4, M9 checklists. Interfaces: M2 provides
selector signatures to M5; M3/M4 provide `render_*_png` to M5's `DEFAULT_RENDERERS`; M5 provides
`convert_bank` to M6/M7; M6/M7 provide the keyword to M8.

## Work packages

One work package per milestone, same ID (WP-M1 ... WP-M10), owner and touch points as above.
Dependencies are the milestone `Depends on` lines. Acceptance criteria are the milestone done
checks. Obvious follow-ons for every package: pyflakes, typing, and ASCII gates green; one
`docs/CHANGELOG.md` bullet.

## Acceptance criteria and gates

- Per-patch gate: `source source_me.sh && pytest tests/test_pyflakes_code_lint.py
  tests/test_function_typing.py tests/test_ascii_compliance.py` plus the milestone's tests. Red
  blocks the next milestone.
- Integration gate (M6, M7): `check_package()` zero violations on the switch-on package; switch-off
  packaged item HTML contains the source fragment verbatim and the ZIP holds no `.png`.
- Readability gate (M3, M4, M9): reviewer three-item checklist over PNGs. One adjustment and
  re-render; a second failure on the same fixture blocks that family's release and sends the plan
  back for revision with the recorded evidence.
- Milestone close: full `pytest tests/` green.

## Test and verification strategy

Permanent tests, each protecting a product contract:

| Test | Protects |
| --- | --- |
| `tests/unit/test_html_to_image_selectors.py` | Which fragments convert: drawings yes, data tables no |
| `tests/unit/test_html_to_image_canvas.py` | SMILES plus options produce a PNG |
| `tests/unit/test_html_to_image_transform.py` | Source bank unchanged; correct replacement; media resolves; cleanup; no residue on error |
| `tests/integration/test_html_to_image_packaging.py` | Switch-on package integrity; switch-off verbatim, both engines |
| `tests/e2e/e2e_html_to_image.py` | CLI flag through real renderers to real packages; evidence artifacts |

No pixel or byte equality anywhere. Playwright never runs inside pytest (browser launch exceeds
the one-second budget); the transform's injectable renderers make that possible. Temporary checks
live in `tests/_temp/` and are deleted at M9.

## Migration and compatibility policy

- Additive and opt-in. Existing callers keep their behavior.
- `BaseItem`, `ItemBank` public API, and item constructors unchanged; bptools keeps working.
- A converted item's `question_text` changes, so its CRC changes -- only inside the derived bank.
- New dependencies are REQUIRED (`docs/REPO_STYLE.md` dependency rule); `rdkit` is already a
  requirement of the content repo that produces these items, and `docs/INSTALL.md` documents the
  Chromium step. A missing browser raises Playwright's own error naming the install command.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Table selector matches a compatible table | Readable table becomes a picture | M2 negative fixture selected | coder | Rule keyed on the stripped drawing attributes (`bgcolor`, cell `border`/`background`, exact `padding: 0`); negatives in the permanent test; feature off by default. Over-selection costs a picture of a readable table; under-selection loses meaning, so the rule errs broad |
| Screenshot unreadable | Image useless | M3/M9 reviewer no | expert_coder | Wrapper style + scale factor; one retry then block and revise |
| RDKit redraw differs from the JS drawing in a way students notice | Wrong interpretation | M4 reviewer no | expert_coder | Only two options exist in the generator and both map directly; reviewer checks methyls and legend |
| Chromium missing on a fresh machine | First conversion errors | `playwright install` skipped | coder | INSTALL step; Playwright's error names the command |
| Derived media dir left after a mid-write failure | Working tree residue | Exception after conversion | coder | Same behavior as the existing staging dir; render-then-commit keeps rendering errors residue-free |
| Plan drift toward a plugin framework | Scope balloons | A third selector proposed | reviewer | List of pairs is the seam; a third pair is one append |

## Rollout and release checklist

- [ ] M1 fixtures captured with provenance
- [ ] M2 selectors green
- [ ] M3 table PNGs pass reviewer checklist
- [ ] M4 canvas PNGs pass reviewer checklist
- [ ] M5 transform contract tests green
- [ ] M6, M7 switch-on integrity and switch-off verbatim green
- [ ] M8 interface and CLI wired
- [ ] M9 E2E runner exits 0; `tests/_temp/` cleared
- [ ] M10 deps declared, docs updated, version bumped, plan archived

## Documentation close-out requirements

- Active plan / progress tracker: this file overwrites `floating-wiggling-castle.md` and is
  mirrored to `docs/active_plans/active/ultra_html_to_image_plan.md`; `git mv` to `docs/archive/`
  at M10.
- docs/CHANGELOG.md entry: one bullet per milestone; fixture provenance and reviewer outcomes under
  "Developer Tests and Notes"; blocked fixtures under "Decisions and Failures".
- Archive / closure notes: `docs/BLACKBOARD_ULTRA_NOTES.md` "Deferred: image follow-up project"
  gains a completion note; `docs/ROADMAP.md` out-of-scope line replaced.

## Patch plan and reporting format

- Patch 1: M1 + M2 (fixtures, selectors)
- Patch 2: M3 (table renderer) -- parallel with Patch 3
- Patch 3: M4 (canvas renderer)
- Patch 4: M5 (transform)
- Patch 5: M6 + M7 (engines, parallel lanes)
- Patch 6: M8 (interface, CLI)
- Patch 7: M9 (E2E, `tests/_temp/` cleared)
- Patch 8: M10 (deps, docs, version, archive)

## Open questions and decisions needed

- Manager/subagent decision procedure: table selector rule.
  - Owner: coder at M2.
  - Rule: start with `bgcolor` attribute or `border` / `background` / exact `padding: 0` in any
    cell style; adjust only when a fixture fails; record the final rule in the module docstring.
- Manager/subagent decision procedure: screenshot wrapper style.
  - Owner: expert_coder at M3.
  - Rule: begin with the body style above and `device_scale_factor=2`; change only on reviewer
    failure, once.
- Non-blocking follow-up: offer the switch on `canvas_qti_v1_2` (its JavaScript is also inert).
- Non-blocking follow-up: retire `biology-problems/table_image_raster_lib.py` (sibling repo's
  decision).
