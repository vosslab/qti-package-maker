# Plan: Single-pass html_to_image conversion with a shared render cache

## Execution status

- M1-M4 complete on 2026-09-30. Final clean pytest: 3,815 passed in 17.00 s,
  including pyflakes, function typing, source line limits, docs consistency, and links.
  All required performance, parity, package integration, browser, and cleanup gates pass.

- 2026-09-30: M1 complete before production edits. Current main: 3,782 pytest tests pass.
- Frozen initial corpus: gel-sizing, restriction, RT-qPCR data, table-curve generators,
  colspan/rowspan markup, and a macromolecule canvas-in-table; six unique tables and one canvas.
- Three-format baseline: 3.7903 s (Canvas 1.6839 s, Blackboard QTI 1.0464 s,
  Blackboard export 1.0600 s); three Chromium launches, 18 table screenshots,
  three canvas draws. All 18 packaged PNGs captured before changes.
- Baseline phases: browser launch 0.6754 s, table rendering 2.7395 s,
  canvas drawing 0.2577 s, tree replacement 0.0033 s. Maximum item PNG payload: 87,766 bytes.
- Final page-strategy prototype: page swap 0.460081 s versus batch 0.459025 s
  (three-run medians). Batching changes one of six decoded images and fails the
  required 25 percent speed improvement. Page swapping preserves every baseline image.
- Scope clarification: the approved ownership design caches per interface/run. Separate
  interfaces can share an explicitly supplied cache; no process-global cache is introduced.
- Custom string finder callbacks retain their constructor contract; shipped finders use
  the single-tree path. Optional M5 is deferred as specified.
- M2 complete: lazy renderer shares one page/font initialization; standalone MathML and
  table/MathML/table reuse are byte- and pixel-identical to the original renderer. Shipped
  conversion performs 54 parses for 54 uncached fields; 18 repeated fields skip parsing.
  Every CanvasSource field participates in the key. Intermediate canvases remain un-packaged.
- M3 complete: final three-format run 3.7903 s -> 0.8854 s, below the original 1.2634 s target;
  launches 3 -> 1, table renders 18 -> 6, canvas renders 3 -> 1. Cache hits/misses 14/7,
  run PNG payload 302,332 bytes. Table work excluding launch 2.7395 s -> 0.4314 s;
  current tree work excluding render calls 0.0059 s. Each engine owns its converted media.
- Coverage correction: initial gel/PCR examples were numeric data tables. Added actual
  GelClassHtml bands from gellib.py and createHtmlTable wells from
  blood_type_agglutination_test.py using immutable committed transform/renderer sources
  as the comparison baseline. Three-format 1.5107 s -> 0.4203 s (original target 0.5036 s),
  launches 3 -> 1, table screenshots 6 -> 2. Every additional PNG and logical package
  member matches (only the Blackboard creation-time comment is normalized).
- Parity gate: all 24 packaged PNGs across both representative corpora have equal dimensions
  and decoded RGBA pixels. Filenames and packaged src/alt values match. Original M1 PNGs
  remain untouched. Evidence lives in output_smoke/html_to_image_baseline/, including
  baseline_metrics.json, post_change metrics/parity, page_strategy strategy_metrics.json,
  mathml_parity results.json, and extended_drawings drawing_extension_report.json.
- M4 integration/browser gates: real CLI -1 -2 -B integrity checks pass; 50-question
  macromolecule -d 50 -x 50 -B -I export passes bptools ZIP validation. Visual inspection
  confirms the molecule next to its information table, readable tables, gel bands, and
  agglutination wells. Firefox/Chromium/WebKit drag, keyboard, grading, recovery, and
  isolation pass; Chromium/WebKit touch alternatives pass. The sandbox Firefox launch
  failed; the unchanged permitted runner passes outside the sandbox.
- Permanent contracts cover rendering shared tables/canvases once across interface engines,
  matching per-item image filenames, source-bank immutability, empty renderer sessions,
  canvas-only banks, and fully cached table banks. All plan-specific temporary probes are
  removed; generated reports/images remain ignored under output_smoke/ for review.
- Optional M5 remains deferred; renderer replacement requires its own follow-up decision.
- Audit follow-up: cache entries now distinguish custom renderer callback identities while
  default table sessions share a stable implementation identity. The shared-cache contract
  covers all three engines, and a red/blue/red regression checks callback changes and reuse.
  The one-third runtime target is recorded as an experiment goal; duplicate renders and
  unnecessary browser launches remain the grounded performance gates.
- Audit follow-up evidence: all 3,822 pytest cases pass. Fresh real Chromium verification
  retains one launch, six table renders, and one canvas render across all three formats;
  all 18 PNGs match the previous verified corpus byte for byte. Its report is retained in
  output_smoke/html_to_image_baseline/audit_fixes/browser_cache_report.json;
  the temporary script is removed.

## Context

`qti_package_maker/html_to_image/` (1081 lines) turns HTML tables and RDKit `<canvas>` drawings
into packaged PNGs. It exists so that Blackboard Ultra, which strips table styles and runs no item
JavaScript, still shows gels, restriction maps, and wells. It is the slowest part of the package,
and the slowness comes from how the work is organized, not from the tables:

- The engines `canvas_qti_v1_2/engine_class.py:261`, `blackboard_qti_v2_1/engine_class.py:254`, and
  `blackboard_export_zip/engine_class.py:152` each call `transform.convert_bank`. A multi-format
  run (`tools/bbq_converter.py:178-186` loops over formats) therefore starts Chromium once per
  format and screenshots every table once per format.
- `transform.convert_bank` (`transform.py:387`) opens `TableRenderer` even when the bank has no
  tables. A canvas-only bank still pays the Chromium startup.
- `TableRenderer.render_table_png` (`render_table.py:151-178`) does all of this for every table,
  one table at a time:
  - opens a new page
  - re-sends about 225 KB of base64 `@font-face` CSS
  - makes two `evaluate` round trips and one locator screenshot
  - closes the page
- The render cache is per item (`transform.py:209`, `cache = {}` at `transform.py:346`). The same
  table in two items gets rendered twice.
- `_convert_html_field` parses and serializes each field several times: finders parse, then
  `_apply_jobs` parses again per family, then the referenced-image scan parses once more
  (`transform.py:219-238`).

The tables themselves are simple. They use borders, background colors, alignment, colors,
monospace, fixed width and height, colspan and rowspan, and inline `sub`, `sup`, `b`, `i`, and
`br`. The one outlier is `table_curve_lib.py`, which draws curves with `border-radius` dots.
Acceptance stays the same: the images must look like the HTML tables. This is a Python-only fix
that keeps Chromium as the renderer and removes the redundant work around it.

## Objectives

- Screenshot each unique table and draw each unique canvas at most once per renderer identity in a shared RenderCache,
  however many items or output formats share it.
- Start Chromium only when at least one table or MathML fragment misses the cache. A run with every
  fragment cached, or with canvases only, starts no browser.
- Pay per-table browser cost only for the table's own content. Font CSS and page setup happen once
  per renderer session.
- Parse each HTML field once per conversion, with no re-parse between the canvas and table stages.
- Keep the PNG output pixel-identical to the current renderer on a representative biology-problems
  corpus. Keep packaged filenames, alt text, and package contents unchanged.

## Design philosophy

- **Fix the design, not the symptom.** The redundancy comes from three things: conversion is owned
  by each engine, the cache is scoped to one item, and each table gets a throwaway page. The plan
  moves cache ownership up to the run level and gives the renderer a session lifetime, rather than
  tuning timeouts or adding parallel browsers.
- The trade-off: a render cache keyed by content costs a little memory (PNG bytes held for the
  run). In exchange, engines stay independent. Each engine still builds, packages, and cleans up
  its own converted bank, so no cross-engine media lifetime is introduced. The rejected
  alternative is converting once and sharing the converted `ItemBank`. That would make the
  interface own the media directory and its invalidation across `add_item`, `trim_item_bank`, and
  `read_package`, which puts lifetime bugs where no one looks.
- Renderer decision: keep Chromium now, and let the optional M5 experiment decide on WeasyPrint.
  - Most of the cost is how the pipeline calls the renderer: conversion repeated per format, a
    cache scoped to one item, a new page per table, and Chromium started even with no tables. All
    of that is needed with either renderer, so it comes first.
  - WeasyPrint writes PDF only, since PNG output was removed in v53. It would need a PDF-to-PNG
    step plus cropping to the table's box.
  - Its layout differs from Chromium, which is what students' browsers use, so exact image parity
    is impossible.
  - It needs the Pango and cairo system libraries. Version 69.0 is installed locally.
  - Its only unique gain is removing about one second of browser startup per run, plus the
    Chromium download.
  - MathML is not a deciding factor. Only `Henderson-Hasselbalch.py` in biology-problems emits
    MathML, as a standalone `<p><math>` outside any table. It is never converted, and
    `render_mathml_png` has no callers. If an equation is ever placed inside a table, WeasyPrint
    could not draw it.
- **Use the scientific method.** Page reuse and batched screenshots are unproven, so they are
  chosen by measurement and pixel comparison (M1, M2), not assumed.
- Evidence strategy for uncertain methods: time each phase on a fixed biology-problems corpus,
  count Chromium launches and screenshots, and pixel-compare every PNG against a baseline captured
  before any change.

## Scope

- Add a baseline harness under `tests/_temp/` that measures conversion time and counts, and
  captures the current PNGs.
- Add a content-keyed `RenderCache` in `html_to_image/`, shared across items and engines within one
  process.
- Launch `TableRenderer` lazily, only on the first table or MathML fragment that misses the cache.
- Give `TableRenderer` one reusable page that loads the font CSS once. Collapse the font-mapping
  and `fonts.ready` calls into a single `evaluate` per table.
- Rework `_convert_html_field` into a single parse, then render, then replace pass on one lxml tree.
- Pass one `RenderCache` from `QTIPackageInterface` to every html_to_image engine in a run. Wire it
  through `tools/bbq_converter.py` automatically.
- Update the changelog and the engine-option docs, and keep `test_docs_consistency.py` passing.

## Non-goals

- Replace Chromium with WeasyPrint or any other renderer. This is a Python-only fix to the Chromium
  path. The renderer triple interface stays stable so another renderer can be tried later.
- Change packaged image filenames (`{item_crc16}_{family}_{n}.png`), alt text, or which fragments
  are selected (`selectors.py` behavior).
- Deduplicate identical PNG files inside one package. That would change filenames and manifests.
- Add parallel browsers, worker processes, or on-disk caches that persist across runs.
- Change the `html_to_image` / `html_to_image_renderers` constructor contract that bptools and the
  tests rely on.
- Regenerate README screenshots.

## Current state summary

The call flow for one engine today:

```text
QTIPackageInterface.save_package(engine, engine_options={"html_to_image": True})
  -> Engine.save_package(item_bank)
       -> transform.convert_bank(item_bank, renderers)
            -> with TableRenderer():              # Chromium launch, always
                 for item: cache = {}            # per-item cache
                   _convert_html_field(...)       # canvas first, then tables
                     finder() parse -> renderer() -> _apply_jobs() re-parse
                   -> new ItemBank + add_image()
       -> write package, converted_bank.cleanup()
```

- `bptools.export_bbq_to_blackboard` (in the sibling biology-problems repo) goes through
  `QTIPackageInterface.save_package` with `engine_options={"html_to_image": True}`. Only `-B` uses
  images there. Multi-format fan-out happens in `tools/bbq_converter.py`.
- Canvas PNGs are prepared before tables and embedded as data URIs inside the table
  (`_inline_rendered_images`). Intermediate canvas PNGs are dropped from the package. This fix
  from 2026-09-29 must survive the rework.
- Tests: `tests/unit/test_html_to_image_transform.py`, `test_html_to_image_selectors.py`,
  `test_html_to_image_render_canvas.py`, `test_html_to_image_render_mathml.py`, and
  `tests/integration/test_html_to_image_packaging.py` (which uses stub renderers).

## Architecture boundaries and ownership

- `html_to_image/render_cache.py` (new): the content-keyed PNG store. Its key is
  `(renderer_identity, family, prepared_fragment_key)` after the audit's renderer-switch fix.
  For canvases the content key is the frozen `CanvasSource` fields; for
  tables it is the prepared table HTML after canvas data-URI inlining. It has no Playwright
  dependency.
- `html_to_image/render_table.py`: the Chromium session only. It exposes the same
  `render_table_png` and `render_mathml_png` methods. Browser startup becomes lazy.
- `html_to_image/transform.py`: tree rewriting and cache lookup. `convert_bank` gains an optional
  `cache: RenderCache | None` parameter. When it is None, a fresh per-call cache is created, so
  direct callers see today's behavior.
- Engines: forward a new optional `html_to_image_cache` constructor option to `convert_bank`.
  Nothing else changes.
- `package_interface.py`: owns one `RenderCache` per `QTIPackageInterface`. It injects the cache
  into `engine_options` whenever `html_to_image` is true.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Review boundary |
| --- | --- | --- |
| M1 | `tests/_temp/` baseline harness | Temporary; not merged as a permanent test |
| M2 / WS-R | `render_table.py` | Patch 1 |
| M2 / WS-T | `render_cache.py`, `transform.py` | Patch 2 |
| M3 | engines, `package_interface.py`, `tools/bbq_converter.py` | Patch 3 |
| M4 | tests, docs, changelog | Patch 4 |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M1 | Baseline | Time, count, and capture PNGs on a fixed corpus | Evidence before change |
| M2 | Renderer and transform | Session page reuse; single-pass tree; RenderCache | Remove per-table and per-item redundancy |
| M3 | Run-wide cache | Interface-owned cache shared by all html_to_image engines | One render per unique fragment per run |
| M4 | Verify and close | Pixel parity, permanent contract test, docs | Prove output unchanged and faster |
| M5 (optional) | WeasyPrint experiment | Time and visually diff WeasyPrint versus the improved Chromium path on the M1 corpus | Settle the renderer choice with evidence |

### Milestone: M1 baseline

- Depends on: none.
- Deliverables:
  - `tests/_temp/html_to_image_baseline.py`. It builds a BBQ corpus from biology-problems
    generators that emit tables (gels, restriction maps, wells, `table_curve_lib.py` curves,
    colspan/rowspan cases), plus the macromolecule canvas-in-table set.
  - The harness records wall time per phase (Chromium launch, per-table screenshot, canvas draw,
    tree rewrite), launch count, screenshot count, and unique-fragment count.
  - It writes every baseline PNG to `output_smoke/html_to_image_baseline/`.
- Entry criteria: current `main` passes `pytest tests/`.
- Exit criteria: the baseline numbers are written into this plan's status notes. The PNG set is
  captured for a three-format run (`-1 -2 -B` equivalent through `bbq_converter`).
- Parallel-plan ready: no. M2 decisions depend on these numbers.

### Milestone: M2 renderer and transform

- Depends on: M1, because the baseline PNGs are needed for the parity gate.
- Deliverables: WP-R1, WP-R2, WP-T1, WP-T2.
- Workstreams: WS-R (renderer), WS-T (transform and cache).
- Entry criteria: baseline PNGs exist.
- Exit criteria:
  - All baseline PNGs match pixel for pixel.
  - Existing html_to_image tests pass.
  - Per-table cost drops measurably against M1.
- Parallel-plan ready: yes. WS-R touches only `render_table.py`; WS-T touches only
  `transform.py` and the new `render_cache.py`. Maximum of 2 lanes. They share only the unchanged
  `render_table_png(str) -> bytes` signature.

### Milestone: M3 run-wide cache

- Depends on: WP-T2, because `convert_bank(cache=...)` must exist.
- Deliverables: WP-E1.
- Entry criteria: M2 exit criteria are met.
- Exit criteria: a three-format run launches Chromium at most once, and every table and canvas
  renders exactly once (confirmed by the M1 harness counts).
- Parallel-plan ready: no. This is a single small patch across the interface and engines.

### Milestone: M4 verify and close

- Depends on: M3.
- Deliverables: WP-V1, WP-D1.
- Exit criteria:
  - Full `pytest tests/` passes.
  - The Playwright self-test drag runner is unaffected.
  - The changelog is updated.
  - `tests/_temp/` checks are promoted or removed.
- Parallel-plan ready: yes. WP-V1 and WP-D1 touch disjoint files. Maximum of 2 lanes.

### Milestone: M5 WeasyPrint experiment (optional)

- Depends on: M4, because the comparison must be against the improved Chromium path, not today's.
- Deliverables: `tests/_temp/weasyprint_table_probe.py`. It renders each M1 corpus table through
  WeasyPrint to PDF, then to PNG with pypdfium2 or pdftoppm, and crops the result. It records the
  time per table and produces side-by-side sheets comparing WeasyPrint and Chromium images.
- Decision rule: adopt WeasyPrint only if all three hold:
  - Total time per run is at least 2x faster than the improved Chromium path.
  - Every table stays readable and faithful on visual review, including the curve,
    colspan/rowspan, and monospace cases.
  - The user accepts images that are not pixel-identical.
  Otherwise keep Chromium and record the result under Decisions and Failures in the changelog.
- Exit criteria: the decision and its numbers are recorded in `docs/CHANGELOG.md`, and the probe is
  removed from `tests/_temp/`.
- Parallel-plan ready: no. This is a single experiment.

## Work packages

### Work package: WP-R1 reuse one page per renderer session

- Owner: coder (WS-R).
- Touch points: `qti_package_maker/html_to_image/render_table.py`.
- Depends on: M1.
- Acceptance criteria:
  - `TableRenderer` creates one page per session and loads the font `<style>` into it once.
  - Each table replaces a single container's contents. The font mapping and `fonts.ready` run in
    one `evaluate`. The screenshot targets the new table element.
  - `render_mathml_png` uses the same page.
  - Browser startup (`sync_playwright().start()`, launch, context) moves from `__enter__` to a
    private `_ensure_started()` that runs on the first render call. `__exit__` closes only what was
    started.
- Decision procedure (page swap versus batch page):
  - Hypothesis A: reusing a page and swapping innerHTML per table removes most of the per-table
    cost.
  - Hypothesis B: laying out all of an item's unique tables in one page and screenshotting each
    element is faster still.
  - Measure both on the M1 corpus. Choose B only if it is at least 25% faster than A and stays
    pixel-identical. Otherwise keep A, the simpler option.
  - Correction path: if either option causes pixel drift (for example font loading or layout
    carrying over from the previous table), reset the container and reuse `set_content` with a
    cached font `<link>` to a `data:` stylesheet instead.
- Security note: the fragment reaches the page by DOM insertion, so `<script>` elements in it do
  not execute. That matches the current trust boundary (ASVS V1.2.1 comment kept).
- Obvious follow-ons: remove the now-unused `new_page`/`close` per call; update the docstring.

### Work package: WP-R2 skip the browser when nothing needs it

- Owner: coder (WS-R).
- Touch points: `render_table.py`.
- Depends on: WP-R1, for the `_ensure_started` hook.
- Acceptance criteria: entering and leaving a `TableRenderer` without rendering starts no Playwright
  process. A unit test uses a monkeypatched `sync_playwright` that fails if it is called.

### Work package: WP-T1 add a content-keyed RenderCache

- Owner: coder (WS-T).
- Touch points: new `qti_package_maker/html_to_image/render_cache.py`.
- Depends on: M1.
- Acceptance criteria:
  - `RenderCache.get_or_render(family, key, render_fn) -> bytes` calls `render_fn` only on a miss.
  - The table key is the prepared HTML string. The canvas key is a tuple of the `CanvasSource`
    fields. That requires `CanvasSource` to be hashable or converted to a tuple; check its
    dataclass definition in `selectors.py`.
  - Hit and miss counters are exposed for the harness and the contract test.
  - No Playwright import.

### Work package: WP-T2 single-pass conversion using the cache

- Owner: coder (WS-T).
- Touch points: `qti_package_maker/html_to_image/transform.py`, and `selectors.py` if a
  tree-level finder helper is needed.
- Depends on: WP-T1.
- Acceptance criteria:
  - `_convert_html_field` parses the field once.
  - Canvas targets are rendered through the cache and replaced in the tree.
  - Outermost tables are serialized with canvas PNGs inlined as data URIs, rendered through the
    cache, and replaced in the same tree.
  - The referenced-image filter runs on that tree, and the field is serialized once.
  - Image names still come from the per-item counters, so filenames are unchanged.
  - The per-item HTML cache stays in place for identical choice strings.
  - `convert_bank(item_bank, renderers=None, cache=None)` creates a fresh `RenderCache` when
    `cache` is None.
  - With default renderers, the `TableRenderer` context is entered but starts Chromium lazily
    (WP-R2).
  - The canvas-inside-nested-tables regression test (added 2026-09-29) still passes unchanged.
- Obvious follow-ons: delete `_apply_jobs` and any finder-based re-parse helpers that become dead
  code. Keep `find_*_fragments` as public selectors if tests use them.

### Work package: WP-E1 share one cache across engines in a run

- Owner: coder.
- Touch points:
  - `package_interface.py`: add a `self.render_cache` created in `__init__` and passed as
    `html_to_image_cache` when `engine_options["html_to_image"]` is true.
  - The three engine `__init__` and `save_package` methods: forward the cache to `convert_bank`.
  - `tools/bbq_converter.py`: no flag change; it benefits automatically.
- Depends on: WP-T2.
- Acceptance criteria:
  - Constructing an engine without `html_to_image_cache` behaves exactly as before.
  - Through the interface, a second html_to_image engine gets 100% cache hits and starts no
    Chromium.
  - `bptools.export_bbq_to_blackboard` needs no change.
- Obvious follow-ons: add the new option to the engine-option docs listed in
  `tests/unit/test_docs_consistency.py`.

### Work package: WP-V1 verification and permanent contract test

- Owner: tester.
- Touch points: `tests/unit/test_html_to_image_transform.py` or
  `tests/integration/test_html_to_image_packaging.py`, and `tests/_temp/`.
- Depends on: WP-E1.
- Acceptance criteria:
  - One permanent test: through `QTIPackageInterface`, save two html_to_image engines with
    counting stub renderers. Assert that each unique fragment renderer runs once in total, and
    that both packages contain the same image filenames. This guards against a regression back to
    per-engine rendering.
  - The temporary pixel-parity check compares every M1 baseline PNG to the new output. They must
    be identical; any difference blocks M4.
  - M1 harness counts are re-run and recorded.
- Obvious follow-ons: delete the `tests/_temp/` harness and parity script once the numbers are in
  the changelog.

### Work package: WP-D1 documentation close-out

- Owner: planner or coder.
- Touch points: `docs/CHANGELOG.md`, `docs/ENGINES.md` (or wherever the html_to_image options are
  documented), `docs/CODE_ARCHITECTURE.md` (html_to_image data flow).
- Depends on: WP-E1.
- Acceptance criteria:
  - The changelog records before and after timings and launch counts.
  - The changelog records the page-swap versus batch decision under Decisions and Failures.
  - `test_docs_consistency.py` passes.

## Acceptance criteria and gates

- Per-patch gate: `source source_me.sh && pytest tests/` passes; pyflakes and typing tests pass;
  no file exceeds 999 lines.
- Parity gate (blocking M2 and M4 exit): every baseline PNG is pixel-identical. Failure means the
  renderer change altered layout or fonts. Fix the page-reset approach (WP-R1 correction path)
  before continuing. Never accept drift by regenerating the baseline.
- Performance gate: a three-format run with unchanged renderers launches Chromium at most once
  and renders each unique prepared fragment once. Failure means inspecting cache wiring and keys
  with the harness profile. Record total conversion time against the M1 baseline; investigate
  measured regressions. The original one-third runtime target is a non-blocking experiment goal,
  because it is not grounded in a product latency requirement (post-audit clarification).
- Integration gate: one real Chromium `-B` export of the macromolecule set passes the bptools
  `_validate_blackboard_export_zip` check, and a visual spot check of one table and one
  canvas-in-table item matches.

## Test and verification strategy

- Fast lane: the existing html_to_image unit and integration tests, plus the WP-R2 lazy-launch
  unit test and the WP-V1 cache contract test. All are offline and use stub renderers.
- Temporary lane (`tests/_temp/`): the M1 timing harness and the pixel-parity script. These use
  real Chromium and RDKit and are run explicitly.
- Browser regression: `tests/playwright/playwright_selftest_drag.py` is unaffected but re-run once
  as a sanity check, since the fonts are shared.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Page reuse leaks layout or font state between tables | Pixel drift in packages | Parity gate diff | WS-R coder | Container reset; fall back to per-table `set_content` with cached font stylesheet |
| Cache key misses a render-affecting input | Wrong image reused | Two fragments that differ only in an unkeyed attribute | WS-T coder | Key tables on full prepared HTML; key canvases on all `CanvasSource` fields |
| Cache memory grows on huge banks | High RSS | Banks with thousands of unique tables | WS-T coder | PNGs are small (tens of KB); record peak size in M1; add eviction only if measured |
| Lazy launch hides a missing-Chromium error until mid-run | Late failure after partial work | First table miss | WS-R coder | Phase 1 still renders fully before any directory is written (`transform.py:342`); error surface unchanged |

## Documentation close-out requirements

- Active plan / progress tracker: copy this plan to
  `docs/active_plans/active/html_to_image_single_pass_plan.md` at execution start and record the
  M1 numbers there.
- docs/CHANGELOG.md entry: record the additions, behavior (no output change), before and after
  timings, and the page-strategy decision.
- Archive / closure notes: `git mv` the plan to `docs/archive/` after M4.

## Patch plan and reporting format

- Patch 1: `render_table.py` lazy session and page reuse (WP-R1, WP-R2).
- Patch 2: `render_cache.py` and single-pass `transform.py` (WP-T1, WP-T2).
- Patch 3: engine and interface cache wiring (WP-E1).
- Patch 4: permanent contract test, docs, changelog, `tests/_temp/` cleanup (WP-V1, WP-D1).

## Open questions and decisions needed

- Manager/subagent decision procedure:
  - Decision owner: WS-R coder, reviewed by the manager.
  - Evidence and decision rule: WP-R1 page swap versus batch page, using the 25% speed and zero
    pixel drift rule on the M1 corpus.
- Non-blocking follow-up: run M5 only if the user wants the WeasyPrint question settled with data.
  A switch would be its own follow-up plan.
