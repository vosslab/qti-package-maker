# Plan: Convert Blackboard Ultra-incompatible HTML into images

## Context

Blackboard Ultra silently degrades several HTML constructs on import. The question survives, the
information does not. Two confirmed cases in this repo's content motivate the work, and they fail
for different reasons.

**CSS-dependent tables.** Ultra strips every CSS declaration. A plain data table still renders,
so most content ports cleanly. What loses meaning is content whose MEANING lives in the CSS:
chemistry structure diagrams drawn as table cells, where `padding:0`, per-edge `border`,
`text-align`, and `colspan`/`rowspan` are the drawing primitives. The canonical case is the
`sugarlib` Fischer and Haworth projections in the sibling `biology-problems` repo
(`problems/biochemistry-problems/carbs/sugarlib.py`):

```html
<table border="0" style="border-collapse: collapse; border: white solid 0px;">
 <td colspan="2" style="border: solid white 0px; padding: 0; text-align: right;">H&nbsp;</td>
```

Ultra drops the styles and the projection collapses into an unreadable run of letters. That same
generator also writes a space between `<tr>` and its first `<td>`, the whitespace-in-`<tr>`
pattern that crashes the Ultra question-expand renderer ("Oops! Something broke.") when the table
carries a `text-align` style. `blackboard_export_zip/common_xml.py sanitize_question_html()`
defuses that crash today, and the information loss remains.

**Canvas diagrams driven by JavaScript.** A second family draws molecules with the RDKit
JavaScript build into an HTML `<canvas>`. `docs/active_plans/audits/rdkit_qti_import_notes.md`
records that this JavaScript executes after BBQ text import and stays inert after Canvas QTI 1.2
and Blackboard QTI 2.1 import, where script content is also escaped or broken. Several engines
already refuse RDKit-bearing items outright (`moodle_aiken/write_item.py:27`,
`human_readable/write_item.py:16`), and `html_selftest` carries CSS specifically to keep RDKit
canvases from overflowing. The learner sees an empty box.

Evidence gathered while planning settles the biggest question about the second case: the source
data survives export. `moleculelib.py:62-73` writes the SMILES string as a literal into the item's
own HTML, next to the canvas id, its width and height, and the `mdetails` drawing-option
dictionary:

```html
<p><canvas id="canvas_<crc>" width="256" height="256"></canvas></p>
<script>...let smiles="CC(N)C(=O)O";let mol=RDKitModule.get_mol(smiles);
mdetails["legend"]="alanine";mdetails["explicitMethyl"]=true;
mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));</script>
```

So the canvas case is a redraw from embedded source data rather than an attempt to recover
pixels. The survey confirms how widely that holds before the canvas renderer commits to it.

These two are the first entries in a longer list. The durable problem is HTML compatibility
remediation: some HTML constructs stop working in Ultra, and the reliable fix for them is an
image. This plan builds that mechanism with an extensible registry, and ships the two confirmed
input classes in the first release.

Charter context: `docs/BLACKBOARD_ULTRA_NOTES.md` lines 724-759 deferred this as an "image
follow-up project" with a four-step charter. Three steps are already satisfied -- gate D PASS
(2026-07-02) proved plain `<img>` imports and renders in Ultra through `blackboard_qti_v2_1` and
`blackboard_export_zip`, and the media layer shipped (`common/media_assets.py`,
`ItemBank.media_base_dir`, `ItemBank.collect_assets()`, `common/zip_writer.py`). Step 1, local
image generation, is the remaining piece and now generalizes past chemistry.

## Objectives

- Detect HTML fragments whose visual meaning or operation stops working after Ultra import,
  render each as a readable image, replace it with an accessible `<img>`, and package the result
  through the existing media pipeline.
- Produce images that preserve the source content's instructional and scientific meaning, judged
  by readability rather than by resemblance to any prior rendering.
- Ship a registry that accepts new fragment types by adding a selector and a renderer, leaving
  the bank transform and engine integration untouched.
- Leave compatible HTML exactly as it is, and report unsupported fragments clearly rather than
  guessing.
- Keep every existing conversion producing the output it produces today until a user opts in.
- Keep the installed package's runtime to pip-installable Python packages.
- Give every generated image a description that conveys the same information as the image,
  independently of the item prompt.

## Design philosophy

The plan leans on three core philosophies from `docs/REPO_STYLE.md`. **Fix the design, not the
symptom**: `sanitize_question_html()` stops the Ultra crash and leaves the diagram unreadable;
engines refusing RDKit items sidesteps the question rather than answering it. Producing a
readable image addresses the actual loss. **Long-term over short-term**: framing this as HTML
compatibility remediation with a registry costs slightly more than two hard-coded converters and
gives the next Ultra incompatibility a place to land. **Focus on important issues**: the
important question is whether a student can read and correctly interpret the result.

The acceptance standard is READABILITY AND PRESERVED MEANING, not visual fidelity. A converted
fragment does not need to resemble Blackboard Classic, a browser, or the original markup. The
renderer may simplify layout, change fonts, adjust spacing, enlarge labels, or redraw the content
in a cleaner form. This is a deliberate choice with a large payoff: the table renderer needs to
produce a readable diagram from the table's structure rather than emulate a CSS engine, which
removes the hardest and least durable part of the work. CSS declarations matter only where they
carry meaning a reader needs -- which side a substituent sits on, which cells group together --
and not as a layout spec to reproduce.

One sentence is the primary design contract, and every renderer answers to it:

> Renderers consume the source representation of a supported fragment and produce a readable
> image preserving the fragment's instructional meaning.

That contract covers CSS tables and RDKit canvases today, and SVG, MathML, or anything else
later, without making the mechanism chemistry-specific. It also leaves renderer capability open:
a renderer whose fragment carries rich source data can rebuild the content, while one whose
fragment carries only markup or an embedded image does what that source allows. The contract asks
for a readable image, not for semantic reconstruction in every case.

The two initial input classes share that contract and split on implementation. A styled table's
source of truth is its markup structure. A canvas molecule's source of truth is the SMILES string
beside it.

This plan fixes OUTCOMES and leaves IMPLEMENTATION open. The acceptance outcomes in
`## Acceptance criteria and gates` are the contract. Structure, drawing approach, font handling,
option mapping, selection method, and API shape are investigation results, chosen by the
implementer from repository evidence and rubric-scored rendering, then recorded in the changelog
when settled.

- Evidence strategy for uncertain methods: M1 surveys Ultra-incompatible HTML broadly, then
  scopes the release to the patterns a renderer can serve, and writes a readability rubric before
  any renderer exists. Each renderer builds its smallest leading candidate and scores it against
  that rubric; a second candidate follows only when the first misses specific criteria, and a
  stop rule bounds the search so failure produces evidence for replanning rather than an
  open-ended project. Milestones complete on rubric scores applied by a `reviewer` agent, so the
  implementation path runs unattended end to end; a human approves the rendered corpus once, as a
  release gate.

## Scope

- Survey Ultra-incompatible HTML broadly: catalog the constructs known or observed to fail or
  lose meaning on import, using this repo's Ultra notes, the RDKit audit notes, and the sibling
  repo's generators as sources.
- Scope the first release to the patterns a renderer can serve, starting with CSS-dependent table
  diagrams and RDKit-generated canvas diagrams.
- Survey enough ordinary, compatible HTML to establish that selection leaves it alone.
- Write a readability rubric with mandatory and scored criteria, applicable by a `reviewer` agent
  to a rendered image plus its source.
- Build a fragment registry: each entry pairs a selector that recognizes a pattern with a
  renderer that turns it into readable image bytes.
- Build the table renderer for CSS-dependent table diagrams, producing a readable reconstruction
  of the table's structure.
- Build the canvas renderer for RDKit canvases, redrawing from the embedded molecular source
  through RDKit's Python drawing API.
- Build the shared replacement and packaging layer: image naming, dedup, alt text, media
  ownership, cleanup, and `<img>` insertion, driven by an `ItemBank -> ItemBank` transform.
- Deliver an opt-in switch at the engine level and at `tools/bbq_converter.py`, defaulting to
  off, with exception-safe cleanup of anything the transform created.
- Declare whatever new runtime dependencies the selected approaches need in
  `pip_requirements.txt` and `pyproject.toml`.
- Add unit, integration, and rubric-scored coverage per `docs/PYTEST_STYLE.md`, with each proof
  step classified as a permanent test, an evidence artifact, or a one-time release check.
- Update the affected docs, including a registry-extension guide so a later contributor can add a
  fragment type.

## Constraints

Requirements every candidate implementation satisfies, independent of the design it lands on.

- The installed runtime uses pip-installable Python packages, so setup stays a single
  `pip install` step.
- Engine defaults stay as they are; the switch stays off until a user sets it.
- The output image format is one Ultra renders, confirmed by gate D PASS evidence.
- Conversion applies only where a registered renderer supports the recognized pattern; every
  other fragment passes through as authored.
- Rendering starts from the fragment's source content, so the result carries the source's meaning
  even when its layout, fonts, and spacing differ from any prior rendering.
- The transform runs on the write side, so a read-side round trip keeps the original markup
  intact.
- The item model, `BaseItem` constructors, and the `ItemBank` public API keep their current
  shape, so bptools generators keep working as written.

## Non-goals

- Reproducing Blackboard Classic or browser pixels stays out; readability is the standard.
- Recovering drawings from canvas pixels stays out; the canvas renderer redraws from source data.
- Executing question JavaScript during conversion stays out.
- Converting arbitrary HTML that no registered renderer recognizes stays out; those fragments
  pass through and are reported.
- Audio and video handling stays reserved for a later plan.
- Changes to the `biology-problems` repo stay owned by that repo; here it is read-only evidence.

## Current state summary

- Media layer is complete and tested. `common/media_assets.py` owns scanning, classification,
  collision-safe naming, `rewrite_html_srcs`, `rewrite_field_value`, `rewrite_item_media`, and
  the four-value `media_policy`. `ItemBank` owns `media_base_dir`,
  `set_media_base_dir(path, owned=)`, `add_image(src, bytes)`, `collect_assets()`, and
  `cleanup()`, which removes `media_base_dir` only when the bank created it.
- `blackboard_export_zip.save_package()` calls `_plan_image_embedding(item_bank)` as step 0,
  ahead of staging-directory creation and item rendering, so a bank-level transform runs ahead of
  that call for its images to be collected. `blackboard_qti_v2_1` has its own collection point to
  locate the same way.
- `base_engine.process_item_bank()` already accepts `item_transform_fn` and `post_render_fn`
  hooks, and `media_assets.rewrite_item_media()` already deep-copies an item before rewriting, so
  "writers render from a copy" is an established, tested invariant with reusable machinery.
- `canvas_qti_v1_2.engine_class` sets the precedent for an engine option: a validated constructor
  keyword plus a settable attribute, kept out of argparse.
- `engines/engine_registration.py` is the repo's existing registry precedent and is worth reading
  before designing the fragment registry.
- Known Ultra incompatibilities are already catalogued in `docs/BLACKBOARD_ULTRA_NOTES.md`,
  including the CSS strip, the `<u>` and heading rewrites, `<pre>` whitespace destruction, SVG
  non-support, and the table-whitespace crash. That catalog is the starting point for the survey.
- RDKit content today: `moodle_aiken/write_item.py:27` and `human_readable/write_item.py:16`
  detect `rdkit` in item text and decline the item; `html_selftest/html_functions.py:184` carries
  responsive CSS for RDKit canvases; `blackboard_export_zip/common_xml.py` passes RDKit script
  markup through verbatim. The molecular source survives in the markup as shown in Context.
- `common/string_functions.py:83 _html_table_to_text()` converts an HTML table to text via
  `tabulate`; its only caller is line 355 in the same module. It is a candidate alt-text source
  whose sufficiency M1 evaluates.
- `common/package_integrity.check_package()` validates manifest resolution, media references, and
  cross-links on a finished package, and is the natural oracle for integration tests.
- `tests/integration/test_staging_dir_leak.py` guards against leaked staging directories and is
  the precedent for the lifecycle coverage in WP-B3.
- Pillow 12.3.0 is present in the local site-packages; neither Pillow nor RDKit is declared in
  `pip_requirements.txt` or `pyproject.toml`. Both ship prebuilt wheels; RDKit draws PNG directly
  through its Python API.
- `pyproject.toml` `[tool.setuptools.package-data]` globs `qti_package_maker = ["data/*"]`; any
  bundled asset in a subdirectory needs a widened glob.
- `biology-problems/table_image_raster_lib.py` solves the inverse problem (data -> colored table
  cells, to survive the sanitizer). It has no importers, and this plan's direction supersedes it
  now that images render in Ultra.

## Architecture boundaries and ownership

Three layers, with the registry as the seam that makes new fragment types cheap.

- **Selection layer.** Walks an item's HTML, recognizes fragments matching registered patterns,
  and classifies each. A fragment is selected only when a registered renderer serves its pattern;
  everything else passes through untouched and is reported. Author markers force selection on or
  off for a recognized fragment.
- **Renderer layer.** A registry entry is a selector, a renderer, and optional metadata such as a
  pattern name. That is the whole abstraction; it is a dispatch table, not a plugin framework, and
  it stays that small until a third or fourth renderer type shows what else it actually needs. A
  renderer is a deterministic computation over its inputs: supported fragment plus a render
  configuration in, readable image bytes out, per the design contract above. Renderers may differ
  in capability -- one may rebuild content from rich source data, another may only redraw what its
  markup carries -- and the registry accommodates both rather than assuming reconstruction.
  Bank knowledge and engine knowledge stay outside. Resolving packaged assets such as fonts is the
  job of a separate loader that produces the render configuration, so a renderer is exercisable
  from inline inputs alone. Renderers stay independent of one another.
- **Replacement and packaging layer.** One shared component owns image naming, dedup, alt-text
  generation, `<img>` insertion, media-directory ownership, and cleanup. Adding a fragment type
  changes the registry and adds a renderer; this layer, the bank transform, and the engine
  integration stay as they are.

Additional boundaries:

- The bank transform returns a NEW `ItemBank`; the caller's bank and items stay as the caller left
  them.
- Filesystem effects are an intended, documented side effect, distinct from bank immutability.
  When the caller supplied `media_base_dir`, the transform writes generated images into
  caller-owned space, documented where the transform is defined. When no directory exists, the
  transform creates one and the derived bank owns it via `set_media_base_dir(path, owned=True)`.
  Whichever component creates the derived bank releases it through `cleanup()`, on both the
  successful and the failing path.
- `assessment_items/` stays as it is.
- Engines gain an opt-in keyword and a call to the transform ahead of their asset collection. All
  other engine logic stays as it is.
- `tools/bbq_converter.py` gains one flag that it forwards to the engine option.

Module count, file names, and function signatures are milestone outputs, chosen to fit the
boundaries above and the conventions already visible in `qti_package_maker/common/`.

Review boundary rule: any work package touching `engines/` demonstrates that a switch-off run
matches `main` behaviorally for the engines it changed and for the shared code paths those
engines exercise.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Review boundary |
| --- | --- | --- |
| M1 / WS-SURVEY | incompatibility catalog, fixtures, provenance, readability rubric | Read-only against the sibling repo |
| M2 / WS-REGISTRY | fragment registry and selection layer | Registry API; renderers stay pluggable |
| M3 / WS-RENDER-TABLE | the table renderer and its asset loader | Deterministic over inputs; bank and engine imports stay out |
| M4 / WS-RENDER-CANVAS | the canvas source extractor and renderer | Deterministic over inputs; independent of the table renderer |
| M5 / WS-BANK | replacement and packaging layer, bank transform, lifecycle | New bank returned; input bank unchanged |
| M6 / WS-ENGINE | Blackboard engine classes | Switch-off output matches `main` |
| M6 / WS-CLI | `tools/bbq_converter.py` | Flag absent keeps today's behavior |
| M7 / WS-TEST | `tests/unit/`, `tests/integration/`, `tests/e2e/` | Structural assertions only |
| M7 / WS-SCORE | rubric scoring task over rendered artifacts | Reviewer agent; runs outside pytest |
| M8 / WS-DOCS | `docs/*.md`, `pyproject.toml`, `VERSION` | Markdown links test green |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M1 | Incompatibility survey and rubric | Catalog Ultra-incompatible HTML, scope the release, write the readability rubric | Evidence-backed fixtures, a scoped pattern list, and an agent-applicable rubric |
| M2 | Fragment registry | Selector/renderer registry and the selection layer | New fragment types plug in without touching the transform |
| M3 | Table renderer | Readable reconstruction of CSS-dependent table diagrams | Table renderer adopted on recorded rubric scores |
| M4 | Canvas renderer | Redraw RDKit canvases from embedded source | Canvas renderer adopted on recorded rubric scores |
| M5 | Transform and packaging | Replacement layer, alt text, dedup, lifecycle | Mixed banks come back as image-bearing banks the media layer resolves |
| M6 | Opt-in integration | Engine keyword plus CLI flag, both defaulting to off | Switch on converts; switch off matches today |
| M7 | Test and evidence | Permanent tests, evidence artifacts, rubric scoring | Suite green; scoped corpus clears the rubric |
| M8 | Docs and release | Capability tables, registry guide, changelog, version | Docs match shipped behavior |

### Milestone: M1 incompatibility survey and rubric

- Depends on: none.
- Deliverables: a catalog of Ultra-incompatible HTML constructs with observed failure modes; a
  release scope naming which patterns this plan serves and which are deferred; fixture sets per
  scoped pattern, each fixture carrying a provenance record; a source-availability finding for
  every canvas-producing path; a compatible-HTML sample for negative evidence; the readability
  rubric; alt-text sufficiency findings.
- Workstreams: WS-SURVEY.
- Entry criteria: none.
- Exit criteria: the catalog draws on `docs/BLACKBOARD_ULTRA_NOTES.md`, the RDKit audit notes,
  and the sibling repo's generators, and states for each construct whether a renderer can serve
  it; the scoped patterns have fixture sets covering their distinct shapes; every canvas-producing
  path is classified by what survives export; the negative sample draws from several
  content-producing paths; each fixture records source revision, pattern class, and generation
  inputs; the rubric names mandatory and scored criteria with a pass threshold and is validated
  against a deliberately degraded rendering; the alt-text findings state what a description must
  convey per pattern class.
- Parallel-plan ready: yes. WP-S1 (incompatibility catalog and scoping), WP-S2 (table fixtures),
  WP-S3 (canvas paths), and WP-S4 (negative sample) are independent; WP-S5 (rubric) merges their
  findings.

### Milestone: M2 fragment registry

- Depends on: M1, because the registry's initial entries are the scoped patterns.
- Deliverables: the registry structure, the selector interface, the renderer interface, and the
  selection layer that walks item HTML and classifies fragments.
- Workstreams: WS-REGISTRY.
- Entry criteria: M1 scoping complete.
- Exit criteria: a registry entry is a selector plus a renderer plus a pattern name, and adding
  one requires no edit to the transform or the engines, demonstrated by registering a trivial
  stub entry in a test; the selection layer recognizes the scoped patterns, leaves the M1 negative
  sample untouched, honors author force-on and force-off markers, and reports every recognized
  fragment with its classification and disposition; a recognized pattern with no registered
  renderer passes through and is reported as unsupported rather than dropped or guessed at.
- Parallel-plan ready: no. The registry and selection layer are one cohesive seam.

### Milestone: M3 table renderer

- Depends on: M1 for fixtures and rubric, M2 for the renderer interface.
- Deliverables: the smallest leading candidate implemented as a bounded prototype and scored;
  further candidates when the first misses, within the stop rule; the adopted renderer and its
  asset loader; any new runtime dependency declared.
- Workstreams: WS-RENDER-TABLE.
- Entry criteria: M1 table fixtures and rubric exist; M2's renderer interface is settled.
- Exit criteria: a `reviewer` agent scores the adopted approach at or above the rubric threshold
  across the full table fixture set, with every mandatory criterion passing; the same input
  rendered twice within one process and one dependency environment yields identical bytes; scores
  and approaches passed over are written up for the changelog.
- Parallel-plan ready: yes, once a comparison begins. Each additional prototype is an independent
  throwaway lane over the same fixtures, merging at the scoring step. A first candidate that
  clears the rubric ends the milestone in one lane.

### Milestone: M4 canvas renderer

- Depends on: M1 for the source-availability finding, fixtures, and rubric; M2 for the renderer
  interface. Independent of M3.
- Deliverables: a source extractor that reads molecular source and drawing options out of the
  fragment; a renderer that redraws through RDKit's Python drawing API and returns readable image
  bytes; the RDKit dependency declared; a documented mapping from source drawing options to their
  Python equivalents.
- Workstreams: WS-RENDER-CANVAS.
- Entry criteria: M1 classified the canvas paths and at least one path carries reusable source.
- Exit criteria: a `reviewer` agent scores the rendered fixture set at or above the rubric
  threshold with every mandatory criterion passing; extraction handles each surveyed path shape or
  raises with the fragment it could not read; option mapping covers the options the survey found,
  with unmapped options recorded rather than silently dropped.
- Parallel-plan ready: yes. Extraction (WP-M1) and rendering (WP-M2) are separable once the source
  shapes are known; they meet at the extractor's output record.

### Milestone: M5 transform and packaging

- Depends on: M2 for selection, M3 and M4 for renderers.
- Deliverables: the shared replacement and packaging layer; the `ItemBank -> ItemBank` transform;
  alt-text generation per pattern class; asset dedup; media-directory lifecycle handling; a
  per-run structured report.
- Workstreams: WS-BANK.
- Entry criteria: both renderer entry points are settled and documented.
- Exit criteria: a mixed bank containing both scoped patterns comes back with images that
  `collect_assets()` resolves; the input bank compares equal to its pre-call state; every
  generated image carries alt text matching the M1 finding for its pattern class; a bank with no
  recognized fragments comes back equal and writes no files; unsupported fragments come back
  unchanged and appear in the report; repeated transform-and-save cycles leave no accumulated
  directories, on both the successful and the failing path.
- Parallel-plan ready: no. Replacement, alt text, dedup, and lifecycle are one cohesive layer.

### Milestone: M6 opt-in integration

- Depends on: M5.
- Deliverables: the opt-in keyword on the two Blackboard engines; the paired CLI flags on
  `tools/bbq_converter.py` defaulting to off.
- Workstreams: WS-ENGINE and WS-CLI, independent once M5 lands.
- Entry criteria: M5 exit criteria met.
- Exit criteria: with the switch off, both changed engines and the shared code paths they
  exercise produce output matching `main` behaviorally (file set, parsed XML structure, item
  content); with the switch on, a mixed bank produces a package containing the rendered images,
  correctly declared and depended on; a save that raises mid-flight leaves no directory behind.
- Parallel-plan ready: yes. WS-ENGINE and WS-CLI touch disjoint files and both depend only on
  M5's entry point.

### Milestone: M7 test and evidence

- Depends on: M3 and M4 for renderer tests, M6 for integration tests.
- Deliverables: permanent unit and integration tests; an artifact-generating E2E script; a
  separate rubric-scoring task; a classification table naming each proof step as a permanent
  test, an evidence artifact, or a one-time release check.
- Workstreams: WS-TEST-UNIT, WS-TEST-INTEGRATION, WS-SCORE.
- Entry criteria: the component under test has a settled entry point.
- Exit criteria: `source source_me.sh && pytest tests/` green; the E2E script renders the scoped
  corpus and writes a scoring manifest; the scoring task returns rubric results at or above
  threshold with mandatory criteria passing; every proof step is classified.
- Parallel-plan ready: yes. Renderer unit tests begin once each renderer settles; integration
  tests wait on M6; scoring runs after the E2E artifacts exist.

### Milestone: M8 docs and release

- Depends on: M6 for behavior, M7 for evidence.
- Deliverables: updated capability, usage, install, and cookbook docs; a registry-extension guide;
  the Ultra notes, RDKit audit notes, and roadmap brought in line with shipped reality; changelog
  entries; CalVer bump in `pyproject.toml` and `VERSION`; release-notes input.
- Workstreams: WS-DOCS.
- Entry criteria: M6 and M7 complete.
- Exit criteria: `pytest tests/test_markdown_links.py` and
  `pytest tests/unit/test_docs_consistency.py` green; `docs/BLACKBOARD_ULTRA_NOTES.md` line 716
  and the "Deferred: image follow-up project" section describe the shipped opt-in behavior;
  `docs/ROADMAP.md` line 49 lists the conversion as delivered;
  `docs/active_plans/audits/rdkit_qti_import_notes.md` records the conversion path as the answer
  to its follow-up question; the registry guide shows a worked example of adding a pattern.
- Parallel-plan ready: no. One writer keeps terminology consistent across the doc set.

## Workstream breakdown

### Workstream: WS-SURVEY

- Goal: replace assumptions with counted evidence, scope the release, and make readability
  scoreable without a human in the loop.
- Owner: reviewer.
- Work packages: WP-S1, WP-S2, WP-S3, WP-S4, WP-S5.
- Needs: read access to the sibling `biology-problems` repo.
- Provides: the incompatibility catalog, release scope, fixtures, provenance, source-availability
  findings, negative sample, rubric, and alt-text findings.
- Review boundary, when modifying the repository: test fixtures, a provenance record, the
  catalog, and the rubric document.

### Workstream: WS-REGISTRY

- Goal: make fragment types pluggable and selection conservative.
- Owner: expert_coder.
- Work packages: WP-G1, WP-G2.
- Needs: WS-SURVEY's scoped pattern list and negative sample.
- Provides: the registry and selection layer every renderer and the transform build on.
- Review boundary, when modifying the repository: the registry and selection components.

### Workstream: WS-RENDER-TABLE

- Goal: adopt the smallest pure-Python approach that renders scoped table diagrams readably.
- Owner: expert_coder.
- Work packages: WP-R1, WP-R2.
- Needs: WS-SURVEY's table fixtures and rubric; WS-REGISTRY's renderer interface.
- Provides: the table renderer registry entry.
- Review boundary, when modifying the repository: the table renderer, its asset loader, and
  dependency manifests.

### Workstream: WS-RENDER-CANVAS

- Goal: redraw canvas diagrams from their embedded source.
- Owner: expert_coder.
- Work packages: WP-M1, WP-M2.
- Needs: WS-SURVEY's canvas fixtures, source-availability findings, and rubric; WS-REGISTRY's
  renderer interface.
- Provides: the canvas renderer registry entry.
- Review boundary, when modifying the repository: the extractor, the canvas renderer, and
  dependency manifests.

### Workstream: WS-BANK

- Goal: replace selected fragments and hand back a media-layer-ready bank.
- Owner: expert_coder.
- Work packages: WP-B1, WP-B2, WP-B3.
- Needs: the selection layer, both renderer entries, and the alt-text findings.
- Provides: the transform both M6 surfaces call.
- Review boundary, when modifying the repository: the replacement layer, the transform, and any
  alt-text helper it promotes.

### Workstream: WS-ENGINE

- Goal: expose the transform as an off-by-default engine option with exception-safe cleanup.
- Owner: coder.
- Work packages: WP-E1, WP-E2.
- Needs: WS-BANK's entry point.
- Provides: the engine-level switch the CLI forwards to.
- Review boundary, when modifying the repository: the two engine classes, with a demonstrated
  switch-off parity check against `main`.

### Workstream: WS-CLI

- Goal: expose the option to educators running the shipped console command.
- Owner: coder.
- Work packages: WP-C1.
- Needs: WS-ENGINE's keyword.
- Provides: the user-facing flag documented in `docs/USAGE.md`.
- Review boundary, when modifying the repository: `tools/bbq_converter.py`.

### Workstream: WS-TEST-UNIT

- Goal: pin registry, renderer, and transform behavior with stable, fast assertions.
- Owner: tester.
- Work packages: WP-T1, WP-T2, WP-T3, WP-T4.
- Needs: settled entry points from WS-REGISTRY, both render workstreams, and WS-BANK.
- Provides: permanent regression coverage.
- Review boundary, when modifying the repository: `tests/unit/`.

### Workstream: WS-TEST-INTEGRATION

- Goal: prove the switch-on path packages correctly, the switch-off path matches today, and
  repeated and failing runs stay clean.
- Owner: tester.
- Work packages: WP-T5, WP-T6.
- Needs: WS-ENGINE and WS-CLI complete.
- Provides: end-to-end evidence for the M6 exit criteria.
- Review boundary, when modifying the repository: `tests/integration/`, `tests/e2e/`.

### Workstream: WS-SCORE

- Goal: apply the rubric to rendered artifacts without embedding agent judgment inside pytest.
- Owner: reviewer.
- Work packages: WP-T7.
- Needs: the E2E artifacts and scoring manifest from WP-T6, the rubric from WP-S5.
- Provides: the rubric results the adoption and release gates read.
- Review boundary, when modifying the repository: a scores file alongside the artifacts.

### Workstream: WS-DOCS

- Goal: make the shipped docs match shipped behavior and show how to extend the registry.
- Owner: planner.
- Work packages: WP-D1, WP-D2.
- Needs: final behavior from M6, evidence from M7.
- Provides: the documentation close-out.
- Review boundary, when modifying the repository: `docs/`, `VERSION`, and the `pyproject.toml`
  version field.

## Work packages

### Work package: WP-S1 catalog Ultra-incompatible HTML and scope the release

- Owner: reviewer.
- Touch points: read `docs/BLACKBOARD_ULTRA_NOTES.md`,
  `docs/active_plans/audits/rdkit_qti_import_notes.md`, and the sibling repo's generators; write a
  catalog and scope note into `docs/active_plans/decisions/`.
- Depends on: none.
- Acceptance criteria: the catalog lists each HTML construct observed or documented to fail or
  lose meaning after Ultra import, with its failure mode and its evidence source; each entry
  states whether an image can carry the lost information and whether a renderer can produce one
  from available source; the release scope names the patterns this plan serves and the ones it
  defers, with a reason per deferral; CSS-dependent table diagrams and RDKit canvas diagrams are
  confirmed in scope on evidence rather than assumption.
- Evidence or review, when useful: the catalog is what keeps selection tied to supported patterns
  rather than a generic judgment that some HTML looks broken.
- Obvious follow-ons: deferred entries become candidate registry additions in a later plan.

### Work package: WP-S2 build the table-diagram fixture set

- Owner: reviewer.
- Touch points: read `biology-problems/problems/biochemistry-problems/carbs/sugarlib.py` and its
  generated output; write fixtures and provenance into this repo's test tree.
- Depends on: WP-S1 scoping.
- Acceptance criteria: the distinct diagram shapes the generator produces are captured as inline
  HTML fixture strings; each fixture carries a SHORT meaning note, a few lines naming only what a
  scorer must check -- which substituent sits on which side, what the backbone order is, whether
  the ring closes -- rather than an exhaustive description of every rendered object; every CSS
  declaration and structural attribute present is counted, marking which ones carry that meaning
  and which are incidental; each fixture records source revision, pattern class, and generation
  inputs; alt-text candidates are generated via `string_functions._html_table_to_text` and
  assessed against outcome 7. The note exists to make scoring possible, so it stays brief enough
  that writing it never becomes a second annotation project.
- Evidence or review, when useful: the meaning notes are what the rubric scores against.
- Obvious follow-ons: hand fixtures and meaning notes to WS-RENDER-TABLE.

### Work package: WP-S3 survey the canvas-producing paths

- Owner: reviewer.
- Touch points: read every RDKit-producing generator in the sibling repo, starting from
  `PUBCHEM/moleculelib.py`, `PUBCHEM/aminoacidlib.py`, and the `PEPTIDES/` generators.
- Depends on: WP-S1 scoping.
- Acceptance criteria: every distinct canvas-producing path is identified and classified by what
  survives export -- molecular source present (SMILES, MolBlock, or other reusable
  representation), drawing options present, highlights present, dimensions present, or none of
  these; the planning-time finding that `moleculelib.py:62-73` embeds the SMILES literal beside
  the canvas is confirmed or corrected across the full set; representative markup is captured as
  inline fixtures with provenance; any path carrying only pixels or only executable code is called
  out explicitly, because it needs a different strategy or a deferral; drawing options actually
  used (`legend`, `explicitMethyl`, stereo annotation, bond indices, highlight arguments) are
  enumerated with counts; alt-text needs are assessed against outcome 7.
- Evidence or review, when useful: the path classification decides whether M4 proceeds as planned.
- Obvious follow-ons: paths with no reusable source are reported for deferral rather than
  expanding M4.

### Work package: WP-S4 sample compatible HTML for negative evidence

- Owner: reviewer.
- Touch points: existing question content in this repo's samples and the sibling repo's
  content-producing generators.
- Depends on: WP-S1 scoping.
- Acceptance criteria: a bounded sample drawn from several distinct content-producing paths,
  covering at least data tables with merged header cells, tables carrying incidental inline
  styling, tables produced by `string_functions`-driven output, and prose with inline markup;
  each sample is captured as an inline fixture with provenance; the sample is sized to bound the
  survey while exercising the shapes most likely to trip a selector.
- Evidence or review, when useful: this sample is what makes the outcome 2 claim meaningful.
- Obvious follow-ons: hand the sample to WS-REGISTRY as the selection contrast set.

### Work package: WP-S5 write the readability rubric

- Owner: reviewer.
- Touch points: a rubric document under `docs/active_plans/decisions/`.
- Depends on: WP-S2, WP-S3.
- Acceptance criteria: the rubric sorts a rendering into one of three buckets -- usable,
  scientifically wrong, or unreadable -- and nothing finer. No criterion references pixel
  similarity, the original layout, or any prior rendering. Four MANDATORY criteria, where any
  failure fails the rendering outright: all labels and symbols present; structural relationships
  unambiguous; stereochemistry, bond direction, alignment, and grouping correct where
  scientifically relevant; and the result interpretable without referring to the original HTML.
  A short list of SCORED criteria covers presentation: text legible at normal Ultra display size,
  and nothing important clipped, overlapped, or visually merged. Each criterion is a yes-or-no
  question a `reviewer` agent answers from the image plus the fixture's meaning note. The rubric
  fits on one page and is validated by scoring at least one deliberately degraded rendering per
  pattern class and confirming each fails. Keeping it this small is deliberate: a scoring
  framework more elaborate than the renderer it judges would cost more to maintain than it
  returns.
- Evidence or review, when useful: the degraded-rendering check proves the rubric discriminates.
- Obvious follow-ons: the rubric becomes the M3 and M4 adoption gate and the WP-T7 scoring input.

### Work package: WP-G1 build the fragment registry

- Owner: expert_coder.
- Touch points: the registry component.
- Depends on: WP-S1.
- Acceptance criteria: a registry entry is a selector, a renderer, and optional metadata such as a
  pattern name, and nothing more; registering an entry requires no edit to the transform, the
  engines, or the replacement layer, demonstrated by registering a stub entry in a test and seeing
  it dispatch; the two interfaces are documented in a short module docstring;
  `engines/engine_registration.py` is read first so this follows the conventions already in the
  repo rather than inventing a second style. Deliberately out of scope for this package: entry
  priority or ordering rules, versioning, capability negotiation, lifecycle hooks, and
  configuration files. Those are added if and when a third renderer type demonstrates the need,
  because two entries cannot show what a general mechanism requires.
- Evidence or review, when useful: the stub-entry test is the extensibility proof.
- Obvious follow-ons: the registry guide in WP-D1 documents the same interfaces.

### Work package: WP-G2 build the selection layer

- Owner: expert_coder.
- Touch points: the selection component.
- Depends on: WP-G1, WP-S4.
- Acceptance criteria: walks an item's HTML and classifies each candidate fragment by registered
  pattern; a fragment is selected only when a registered renderer serves its pattern; the full
  WP-S4 negative sample passes through untouched; recognized-but-unserved fragments pass through
  and are reported as unsupported; author markers force selection on and off for a recognized
  fragment, so the heuristic is always overridable; each run emits a structured report reusing the
  itemized shape of the existing `media_assets` warning stream with an added severity field, so
  conversions and author overrides read as informational events while unsupported fragments and
  genuine problems read as warnings.
- Evidence or review, when useful: the negative sample stays untouched; the scoped corpora select.
- Obvious follow-ons: surface the informational report through the CLI's existing verbose channel.

### Work package: WP-R1 build and score the leading table candidate

- Owner: expert_coder.
- Touch points: a bounded prototype plus the rendered output it produces.
- Depends on: WP-S2, WP-S5, WP-G1.
- Acceptance criteria: the smallest approach that could render the scoped table fixtures readably
  in pure Python is implemented as a bounded prototype and run over the full fixture set; because
  the standard is readability rather than fidelity, the prototype is free to redraw the structure
  cleanly -- consistent spacing, larger labels, simplified rules -- rather than emulate the source
  styling; a `reviewer` agent scores the output against the rubric; when the score clears the
  threshold with every mandatory criterion passing, the approach is adopted and the milestone
  proceeds on one lane; when it misses, the write-up names the failing criteria and a second
  approach targeting those criteria is built and scored the same way. Stop rule: after three
  scored candidates, or after two candidates fail the same mandatory criterion, the work package
  ends and reports its evidence for replanning.
- Evidence or review, when useful: rubric scores from a `reviewer` agent are the deciding
  measurement, so adoption completes without waiting on a person.
- Obvious follow-ons: when the stop rule triggers, hand the failing criteria and candidate
  write-ups back for a scope decision.

### Work package: WP-R2 build the adopted table renderer

- Owner: expert_coder.
- Touch points: the table renderer, its asset loader, and dependency manifests.
- Depends on: WP-R1.
- Acceptance criteria: the adopted approach becomes a registry-conformant renderer from one
  fragment plus a render configuration to image bytes, with bank and engine coupling kept out;
  packaged assets such as fonts are resolved by a separate loader that builds the render
  configuration, so the renderer is exercisable from inline inputs alone; rendering the same input
  twice within one process and one dependency environment yields identical bytes; input outside
  the supported shape raises with the offending fragment, keeping failures loud per
  `docs/PYTHON_STYLE.md`; the entry point and the meaning-carrying constructs it honors are
  documented in the module docstring; any new dependency is declared in `pip_requirements.txt` and
  `pyproject.toml`, and `pytest tests/test_import_requirements.py` stays green.
- Evidence or review, when useful: reviewer confirms the module follows the direct-access and
  explicit-failure conventions in `docs/PYTHON_STYLE.md`.
- Obvious follow-ons: register the entry.

### Work package: WP-M1 build the canvas source extractor

- Owner: expert_coder.
- Touch points: the extractor component.
- Depends on: WP-S3.
- Acceptance criteria: reads a fragment and returns a record carrying the molecular source, its
  representation kind, the drawing options present, any highlight arguments, the requested
  dimensions, and the canvas identifier linking script to canvas; handles each source shape WP-S3
  catalogued; markup naming a canvas without recoverable source raises with the fragment it could
  not read, so the gap is visible rather than silently skipped; extraction reads the markup as
  data and never executes it.
- Evidence or review, when useful: run over the full WP-S3 fixture set and confirm every
  classified path either yields a record or raises with a readable message.
- Obvious follow-ons: hand the record shape to WP-M2.

### Work package: WP-M2 build the canvas renderer

- Owner: expert_coder.
- Touch points: the canvas renderer and dependency manifests.
- Depends on: WP-M1, WP-S5, WP-G1.
- Acceptance criteria: a registry-conformant renderer that turns an extractor record into readable
  image bytes through RDKit's Python drawing API; because readability is the standard, the
  renderer is free to choose sizing, label scale, and layout that read well in Ultra rather than
  matching the JavaScript canvas; the mapping from source drawing options to their Python
  equivalents is documented, covers every option WP-S3 counted, and records any option it cannot
  map rather than dropping it silently; a `reviewer` agent scores the rendered fixture set at or
  above the rubric threshold with every mandatory criterion passing; unparseable molecular source
  raises with the source string; `rdkit` is declared in `pip_requirements.txt` and
  `pyproject.toml`, with any needed import alias added to `tests/test_import_requirements.py`; a
  clean-venv install renders the fixture set.
- Evidence or review, when useful: the rubric's mandatory criteria guard against a rendering that
  reads cleanly and misstates stereochemistry.
- Obvious follow-ons: register the entry.

### Work package: WP-B1 build the replacement and packaging layer

- Owner: expert_coder.
- Touch points: the replacement layer component.
- Depends on: WP-G2, WP-R2, WP-M2, and the WP-S2 and WP-S3 alt-text findings.
- Acceptance criteria: given a selected fragment and its rendered bytes, this layer owns image
  naming, dedup by source identity, alt-text generation per pattern class, and `<img>` insertion
  in place of the fragment; for canvas conversions the canvas element and its companion script are
  both replaced, so no inert markup is left behind; alt text conveys the same information as the
  image, independently of the item prompt, reusing `string_functions._html_table_to_text`
  (promoted to a public name, with its one internal caller updated) where table text meets the bar
  and composing a pattern-aware description otherwise; adding a registry entry requires no change
  here beyond an alt-text strategy for the new pattern class.
- Evidence or review, when useful: independent reviewer confirms canvas items leave no orphan
  script.
- Obvious follow-ons: none.

### Work package: WP-B2 build the bank transform

- Owner: expert_coder.
- Touch points: the transform component.
- Depends on: WP-B1.
- Acceptance criteria: walks every HTML-bearing field using the same field-shape recursion
  `media_assets.rewrite_field_value` already applies (string, list, dict leaves); runs selection,
  dispatch, and replacement over each field; files land where `collect_assets()` resolves them; a
  NEW `ItemBank` is returned and the input bank compares equal to its pre-call state; a bank with
  no recognized fragments comes back equal and writes no files; unsupported fragments come back
  unchanged and appear in the run report.
- Evidence or review, when useful: independent reviewer confirms input-bank integrity.
- Obvious follow-ons: none.

### Work package: WP-B3 define the media-directory lifecycle

- Owner: expert_coder.
- Touch points: the transform component; `tests/integration/`.
- Depends on: WP-B2.
- Acceptance criteria: when the caller supplied `media_base_dir`, the transform writes into it,
  and that filesystem side effect on caller-owned space is documented where the transform is
  defined; when no directory exists, the transform creates one and the derived bank owns it via
  `set_media_base_dir(path, owned=True)`; filename collisions between a generated image and an
  existing file in a caller-supplied directory resolve deterministically without overwriting
  caller content, and the chosen behavior is documented; a transform that raises partway leaves no
  partially written generated files; the component that created the derived bank releases it
  through `cleanup()` on both the successful and the failing path, using the repository's
  established cleanup pattern found by reading how existing engines guard their staging
  directories; repeated transform-and-save cycles over the same source bank leave no accumulated
  directories, verified in the style of `tests/integration/test_staging_dir_leak.py`; the no-op
  path creates nothing.
- Evidence or review, when useful: independent reviewer traces ownership through one caller-owned
  run, one transform-owned run, and one deliberately failing run.
- Obvious follow-ons: none.

### Work package: WP-E1 add the engine option to blackboard_export_zip

- Owner: coder.
- Touch points: `engines/blackboard_export_zip/engine_class.py`.
- Depends on: WP-B3.
- Acceptance criteria: a validated, settable opt-in keyword defaulting to off, following the
  `canvas_src_variant` precedent; `save_package()` runs the transform ahead of
  `_plan_image_embedding` so generated images are collected, and releases the derived bank per the
  WP-B3 lifecycle on both the successful and the failing path; with the switch off the engine
  follows exactly its current code path;
  `pytest tests/integration/test_blackboard_export_zip_output.py` green with its existing
  assertions intact.
- Evidence or review, when useful: diff a switch-off package against one built from `main` and
  show the file set and parsed XML structure match.
- Obvious follow-ons: none.

### Work package: WP-E2 add the engine option to blackboard_qti_v2_1

- Owner: coder.
- Touch points: `engines/blackboard_qti_v2_1/engine_class.py`.
- Depends on: WP-B3. Independent of WP-E1.
- Acceptance criteria: same contract as WP-E1, with the transform placed ahead of this engine's
  own asset collection point, located by reading the engine rather than assumed;
  `pytest tests/integration/test_qti_writer_media.py` green with its existing assertions intact.
- Evidence or review, when useful: same switch-off parity diff as WP-E1.
- Obvious follow-ons: none.

### Work package: WP-C1 add the bbq_converter flag

- Owner: coder.
- Touch points: `tools/bbq_converter.py`.
- Depends on: WP-E1 and WP-E2.
- Acceptance criteria: a paired on/off flag with `parser.set_defaults(...)` holding it off,
  matching the repo's argparse boolean convention; the value reaches any selected engine that
  accepts it, and engines without the keyword run as they do today; a run without the flag
  produces the same output as today; the conversion report surfaces through the existing verbose
  channel; `pytest tests/integration/test_bbq_converter_cli.py` green.
- Evidence or review, when useful: run the CLI both ways on a BBQ file carrying both scoped
  patterns.
- Obvious follow-ons: add the flag to the `docs/USAGE.md` flag table.

### Work package: WP-T1 unit-test the registry and selection layer

- Owner: tester.
- Touch points: `tests/unit/`.
- Depends on: WP-G1, WP-G2.
- Acceptance criteria: a stub registry entry registered in the test dispatches without any
  production edit; a fragment matching a registered pattern is selected; the negative-sample
  fixtures pass through untouched; a recognized-but-unserved fragment passes through and is
  reported unsupported; force-on and force-off markers override the selector in both directions;
  report entries carry the expected severity.
- Evidence or review, when useful: the stub-entry case is the permanent extensibility guard.
- Obvious follow-ons: none.

### Work package: WP-T2 unit-test the table renderer

- Owner: tester.
- Touch points: `tests/unit/`.
- Depends on: WP-R2.
- Acceptance criteria: inline, self-contained fragment strings; asserts properties that hold
  across a dependency upgrade -- output carries the image format's magic bytes, dimensions grow
  when content grows, a rendered image carries more than one distinct pixel value, and two renders
  of one input inside the same test process match; readability stays with the rubric rather than
  pixel assertions here; each test runs in well under one second.
- Evidence or review, when useful: reviewer checks each assertion against the good-test checklist
  in `docs/PYTEST_STYLE.md`.
- Obvious follow-ons: none.

### Work package: WP-T3 unit-test extraction and canvas rendering

- Owner: tester.
- Touch points: `tests/unit/`.
- Depends on: WP-M1, WP-M2.
- Acceptance criteria: inline markup strings covering each surveyed source shape; asserts the
  extractor returns the expected molecular source, options, and dimensions for known markup, and
  raises with the fragment for markup carrying no recoverable source; asserts the renderer returns
  image bytes carrying the format's magic bytes, that a requested size change moves the output
  dimensions, and that two renders of one record inside the same test process match; chemical
  correctness stays with the rubric.
- Evidence or review, when useful: none required.
- Obvious follow-ons: none.

### Work package: WP-T4 unit-test the transform and packaging layer

- Owner: tester.
- Touch points: `tests/unit/`.
- Depends on: WP-B2, WP-B3.
- Acceptance criteria: uses `tmp_path` for the media directory; asserts a selected table fragment
  becomes an image reference with alt text, a canvas plus its companion script become a single
  image reference with alt text, negative-sample content comes back as the same markup, the input
  bank compares equal after the call, `collect_assets()` on the result resolves the new images,
  identical sources resolve to one file, a bank with no recognized fragments writes no files, a
  caller-supplied directory survives `cleanup()` while a transform-created one is removed, and a
  transform that raises partway leaves no generated files.
- Evidence or review, when useful: none required.
- Obvious follow-ons: none.

### Work package: WP-T5 integration-test switch-on packaging

- Owner: tester.
- Touch points: `tests/integration/`.
- Depends on: WP-E1, WP-E2.
- Acceptance criteria: builds a small bank containing one table diagram and one canvas diagram,
  saves with the switch on into `tmp_path` through both Blackboard engines, and asserts the
  package contains both images, the manifest declares them as `webcontent`, the items carry
  `<dependency>` entries, and `common/package_integrity.check_package()` returns zero violations;
  a switch-off run of the same bank asserts the original markup comes through intact; several
  consecutive switch-on saves leave no accumulated directories; a save forced to fail mid-flight
  leaves no directory behind.
- Evidence or review, when useful: reuse the existing integrity checker as the cross-reference
  oracle.
- Obvious follow-ons: none.

### Work package: WP-T6 add the artifact-generating E2E script

- Owner: tester.
- Touch points: `tests/e2e/`.
- Depends on: WP-R2, WP-M2, WP-S5.
- Acceptance criteria: renders the scoped fixture corpus into a reused `output_smoke/` directory
  and writes a scoring manifest listing, per rendered image, its path, its source fixture, that
  fixture's provenance and meaning notes, and the rubric criteria to apply; the script makes only
  mechanical checks -- it exits non-zero when a render raises or produces a single-color image --
  and leaves every judgment call to WP-T7, so it stays a deterministic offline script with no
  agent invocation, no network access, and no special infrastructure; the existing
  `collect_ignore` keeps it out of `pytest tests/`; the `e2e_*.py` name keeps
  `pytest tests/test_test_naming_conventions.py` green.
- Evidence or review, when useful: the manifest is the handoff contract to WS-SCORE.
- Obvious follow-ons: none.

### Work package: WP-T7 score the rendered artifacts against the rubric

- Owner: reviewer.
- Touch points: a scores file written alongside the WP-T6 artifacts.
- Depends on: WP-T6, WP-S5.
- Acceptance criteria: a `reviewer` agent reads the scoring manifest, inspects each rendered image
  against its fixture's meaning notes, and records a pass or fail per rubric criterion plus the
  aggregate result; any mandatory-criterion failure marks the rendering failed regardless of the
  aggregate; the scores file names the rubric revision it applied; the task runs as a plan task
  outside pytest, so no agent judgment sits inside the test suite.
- Evidence or review, when useful: this file is what the adoption and release gates read.
- Obvious follow-ons: rerun after any renderer change that could move output.

### Work package: WP-D1 update capability docs and write the registry guide

- Owner: planner.
- Touch points: `docs/ENGINES.md`, `docs/USAGE.md`, `docs/COOKBOOK.md`, `docs/INSTALL.md`,
  `docs/FORMATS.md`, and a new registry-extension section.
- Depends on: WP-C1.
- Acceptance criteria: `docs/ENGINES.md` records the conversion capability for the two Blackboard
  engines; `docs/USAGE.md` documents the CLI flag and its off-by-default posture;
  `docs/COOKBOOK.md` gains a worked recipe per shipped pattern; the registry guide covers exactly
  three things -- write a selector, write a renderer, register the entry -- with one worked
  example, and states plainly that conversion covers the patterns the registry serves rather than
  arbitrary HTML. The guide stays at that level and leaves internal details undocumented, since
  they will change once a third renderer type lands;
  `docs/INSTALL.md` names the new dependencies; `pytest tests/test_markdown_links.py` and
  `pytest tests/unit/test_docs_consistency.py` green.
- Evidence or review, when useful: none required.
- Obvious follow-ons: none.

### Work package: WP-D2 close out notes, roadmap, and release docs

- Owner: planner.
- Touch points: `docs/BLACKBOARD_ULTRA_NOTES.md`,
  `docs/active_plans/audits/rdkit_qti_import_notes.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`,
  `docs/NEWS.md`, `docs/RELEASE_HISTORY.md`, `VERSION`, `pyproject.toml`.
- Depends on: WP-D1, M7.
- Acceptance criteria: the porting-forecast row at `docs/BLACKBOARD_ULTRA_NOTES.md:716` describes
  the shipped opt-in conversion; the "Deferred: image follow-up project" section records that
  charter step 1 shipped pure-Python as a general remediation mechanism and that steps 2 through 4
  were already satisfied by gate D PASS; the incompatibility catalog is linked from the Ultra
  notes so the deferred patterns stay visible; the RDKit audit notes record the conversion path as
  the answer to their follow-up question; `docs/ROADMAP.md:49` lists the conversion as delivered;
  a CalVer bump lands in both `VERSION` and `pyproject.toml`; the changelog carries the survey
  findings, the release scoping decisions, the source-availability classification, and the
  renderer scores including approaches passed over, under "Decisions and Failures".
- Evidence or review, when useful: none required.
- Obvious follow-ons: consider archiving `docs/active_plans/active/image_support_plan.md` to
  `docs/archive/` with `git mv`, since this plan discharges its last deferred follow-on.

## Acceptance criteria and gates

These seven outcomes are the contract. An implementation meeting all seven is acceptable
regardless of the structure it arrives at.

1. Every supported incompatible-HTML fixture becomes a readable image that preserves the source
   content's instructional and scientific meaning, scored at or above the rubric threshold with
   every mandatory criterion passing.
2. Compatible HTML comes through unchanged.
3. Fragments no registered renderer serves come through unchanged and are reported clearly.
4. Generated images flow through the existing media pipeline: `collect_assets()` resolves them,
   the manifest declares them, items depend on them, and
   `package_integrity.check_package()` returns zero violations.
5. The source bank comes back from the transform equal to its pre-call state; filesystem effects
   are confined to the documented media directory, and repeated or failing cycles leave nothing
   accumulated.
6. The feature is opt-in, and switch-off output matches `main` behaviorally for the two changed
   engines and the shared code paths they exercise.
7. Each generated image carries an accessible description conveying the same information as the
   image, without depending on the item prompt.

Gates:

- Per-patch gate, proportional to what the patch touches. Patches changing Python under
  `qti_package_maker/` or `tools/` run `source source_me.sh && pytest tests/` plus
  `pytest tests/test_pyflakes_code_lint.py tests/test_function_typing.py
  tests/test_ascii_compliance.py`. Patches confined to fixtures, rubric text, catalogs, or
  documentation run the checks covering them -- `pytest tests/test_ascii_compliance.py
  tests/test_markdown_links.py tests/unit/test_docs_consistency.py` -- since the full suite adds
  no signal for a text-only change.
- Milestone integration gate: the complete suite runs at each milestone close regardless of what
  the individual patches touched.
- Adoption gate (M3 and M4 exit): outcome 1 met for that renderer, scored by WP-T7.
- Extensibility gate (M2 exit): a stub registry entry dispatches with no production edit outside
  the registry.
- Integration gate (M6 exit): outcomes 4, 5, and 6 met, verified behaviorally rather than
  byte-for-byte, since package metadata and entry order vary run to run.
- Independent review gate: an independent `reviewer` agent audits the transform and the first
  engine wiring against outcomes 4 and 5.
- Release approval gate: the implementation path from M1 through M8 completes unattended on agent
  gates; shipping the release then requires human approval of the rendered corpus. Human judgment
  gates the release, and no milestone waits on it.

## Test and verification strategy

Each proof step is classified so the permanent suite stays fast and one-time checks stay visible.

| Proof step | Classification | Where it lives |
| --- | --- | --- |
| Registry extensibility via stub entry | Permanent regression test | `tests/unit/` |
| Selection over scoped and negative fixtures | Permanent regression test | `tests/unit/` |
| Renderer structural properties | Permanent regression test | `tests/unit/` |
| Extractor record shapes and error paths | Permanent regression test | `tests/unit/` |
| Transform contracts, dedup, lifecycle | Permanent regression test | `tests/unit/` |
| Switch-on packaging and integrity | Permanent regression test | `tests/integration/` |
| Repeated and failing save cleanliness | Permanent regression test | `tests/integration/` |
| Switch-off parity against `main` | One-time release check per engine change | Reviewer diff, recorded in the patch report |
| Rendered corpus artifacts and manifest | Evidence artifact | `tests/e2e/`, into `output_smoke/` |
| Rubric scores over those artifacts | Evidence artifact | WP-T7 scores file |
| Rubric validation against degraded renderings | One-time check at rubric authoring | WP-S5 write-up |
| Comparison prototypes and their scores | Evidence artifact | WP-R1 write-up, changelog |
| Clean-venv install and render | One-time release check | Rollout checklist |

- Unit tests use inline inputs and `tmp_path`, stay deterministic and offline, and finish well
  under one second each.
- Integration tests verify through the existing `package_integrity.check_package()` and the
  staging-leak pattern already in the suite.
- Readability is never asserted in pytest. It is a judgment about whether a person can read and
  correctly interpret the image, so it lives in the rubric scores, and the permanent suite asserts
  only mechanical properties.
- Determinism scope: identical bytes are expected for the same input within one process and one
  dependency environment, which is what the unit tests assert and what makes dedup stable. Across
  environments, a font or library version legitimately shifts output, so permanent tests read
  structural behavior -- format magic bytes, relative size ordering, pixel variety, and the markup
  transformation itself -- per the brittle-test guidance in `docs/PYTEST_STYLE.md`.
- Failure semantics: a red per-patch gate blocks the next patch. A failed adoption gate blocks
  that renderer from closing while the other renderer, the registry, and selection work continue.

## Migration and compatibility policy

- The feature is additive and opt-in. Existing callers, scripts, and pipelines keep their current
  behavior until they pass the switch.
- Item model, `BaseItem` constructors, and the `ItemBank` API stay as they are, so `bptools`
  generators in the sibling repo keep working as written.
- Converting a fragment changes an item's `question_text` and therefore its CRC identity. That is
  correct -- the converted item IS different content -- and it applies only inside the derived bank
  the transform returns, leaving the caller's bank at its original identity. Document this where
  the transform is defined and in `docs/COOKBOOK.md`.
- Engines that currently decline RDKit-bearing items keep declining them; this plan changes what
  the two Blackboard engines can carry and leaves the text-only engines' contracts alone. Whether
  those engines should accept converted items is a follow-up question, recorded below.
- New runtime dependencies are declared rather than optional, following `docs/REPO_STYLE.md`
  ("we want to require all dependencies, rather than provide work-arounds if they are missing")
  and the user's explicit decision. The single-pip-step constraint keeps the install simple.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Selection converts content that reads fine in Ultra | A readable fragment becomes a picture | WP-S4 negative sample selects | expert_coder | Selection fires only for registered patterns backed by the WP-S1 catalog, tested against a multi-path negative sample, with author overrides both directions and the feature off by default |
| A rendering reads cleanly and states the science wrongly | Students learn the wrong structure | WP-T7 mandatory criterion fails, or release approval rejects | reviewer | Mandatory rubric criteria cover stereochemistry, bond direction, grouping, and label completeness; WP-S5 validates the rubric against degraded renderings; release approval stays a human gate |
| Some canvas paths carry no reusable source | That subset stays unconverted | WP-S3 classifies a path as pixels-or-code only | reviewer | WP-S3 makes the classification explicit before M4 commits; uncovered paths are deferred and reported rather than absorbed |
| Every table candidate misses the rubric threshold | Outcome 1 unmet for that pattern | Adoption gate fails at M3 exit | expert_coder | Readability rather than fidelity is the target, which removes the hardest constraint; the WP-R1 stop rule ends the search after three candidates or a repeated mandatory failure and reports evidence for replanning |
| Registry seam leaks into the transform | Adding a pattern later requires edits across the stack | Stub-entry test needs a production edit | expert_coder | The extensibility gate at M2 exit is exactly this check, and WP-T1 keeps it permanent |
| Alt text loses information the image carries | Screen-reader users get less than sighted users | WP-S2 or WP-S3 sampling shows text falls short | reviewer | Sufficiency is an explicit finding per pattern class, judged prompt-independently; WP-B1 composes a pattern-aware description when plain text falls short |
| Generated files collide with or overwrite caller content | A caller's media directory loses a file | WP-B3 collision check fails | expert_coder | WP-B3 makes collision behavior explicit and non-destructive, and documents the side effect on caller-owned space |
| A failing save leaks a directory | Long runs fill the working tree | WP-T5 failure-path check fails | coder | WP-B3 adopts the repository's established exception-safe cleanup pattern; WP-T5 exercises the failing path |
| Transform runs after an engine's asset collection | Generated images stay outside the package | WP-T5 fails | coder | Each engine's collection point is located by reading the engine; WP-T5 asserts both images are present |
| Dependency version drift changes rendering | Size-sensitive tests redden on upgrade | A dependency bump reddens CI | tester | Structural assertions by design; determinism scoped to one process and environment; rubric rescoring covers readability |
| Input bank altered by the transform | A caller's bank changes underneath them mid-pipeline | Independent review or WP-T4 catches it | reviewer | Deep-copy contract mirroring `rewrite_item_media`; dedicated assertion in WP-T4 and a named independent review gate |
| Design settles before the survey lands | The implementation encodes assumptions the corpus contradicts | Renderer code appears before M1 completes | reviewer | M1 gates M2 through M4; each adoption write-up names what its survey showed |
| Scope growth toward arbitrary HTML rasterization | Milestones balloon; the mechanism overpromises | Support appears for patterns absent from the catalog | reviewer | The release scope is the WP-S1 list; further patterns arrive as registry entries in a later plan, and the docs say so plainly |
| Registry grows into a plugin framework before two entries justify it | Maintenance cost exceeds the value; the seam ossifies around guesses | Priority rules, versioning, capability negotiation, lifecycle hooks, or config files appear in WP-G1 | reviewer | WP-G1 names those as out of scope; the entry stays selector plus renderer plus optional metadata until a third renderer type shows what is actually needed |
| Rubric or meaning notes grow into their own project | Evidence work outruns the implementation it serves | A meaning note exceeds a few lines, or the rubric outgrows one page | reviewer | Both are capped by their work packages; the rubric sorts into three buckets and the notes record only what a scorer checks |

## Rollout and release checklist

- [ ] Incompatibility catalog written and the release scope decided with reasons per deferral
- [ ] Fixture sets committed with provenance and meaning notes; alt-text findings written
- [ ] Canvas source-availability classification complete for every canvas-producing path
- [ ] Compatible-HTML negative sample committed
- [ ] Readability rubric written, mandatory criteria named, validated against degraded renderings
- [ ] Registry extensibility demonstrated by a stub entry dispatching with no production edit
- [ ] Table renderer adopted on recorded rubric scores; approaches passed over documented
- [ ] Canvas renderer adopted on recorded rubric scores; option mapping documented
- [ ] New dependencies declared and verified from a clean-venv install
- [ ] Switch-off parity demonstrated for both changed engines and their shared code paths
- [ ] Switch-on package passes `package_integrity.check_package()` with zero violations
- [ ] Repeated and failing saves verified to leave nothing accumulated
- [ ] `source source_me.sh && pytest tests/` green at every milestone close
- [ ] Docs updated including the registry guide; `pytest tests/test_markdown_links.py` green
- [ ] CalVer bump synchronized across `VERSION` and `pyproject.toml`
- [ ] `docs/NEWS.md` and `docs/RELEASE_HISTORY.md` carry the opt-in conversion highlight
- [ ] Human approval of the rendered corpus, as the release gate

## Documentation close-out requirements

- Active plan / progress tracker: mirror this plan to
  `docs/active_plans/active/ultra_html_conversion_plan.md` at dispatch; `git mv` it to
  `docs/archive/` at close. The WP-S1 catalog and WP-S5 rubric live in
  `docs/active_plans/decisions/`.
- docs/CHANGELOG.md entry: one per patch, "Patch N: [component] [intent]". Record the
  incompatibility catalog, the release scoping decisions, the source-availability classification,
  the alt-text sufficiency findings, and the renderer scores including approaches passed over,
  under "Decisions and Failures", so the log stays useful for later review.
- Archive / closure notes: update `docs/BLACKBOARD_ULTRA_NOTES.md` (line 716 forecast row and the
  "Deferred: image follow-up project" section),
  `docs/active_plans/audits/rdkit_qti_import_notes.md`, and `docs/ROADMAP.md` (line 49) so the
  deferred-work record matches shipped reality; consider archiving
  `docs/active_plans/active/image_support_plan.md` in the same pass.

## Patch plan and reporting format

Patch boundaries follow the work packages above, one patch per completed package, reported as
"Patch N: [component] [intent]". The count follows from how the packages actually land rather than
from a schedule fixed in advance; M3 in particular produces one patch when the leading candidate
clears the rubric and more when the comparison runs to its stop rule.

## Open questions and decisions needed

Each of these is settled by evidence during execution rather than in advance.

- Manager/subagent decision procedure: which incompatible-HTML patterns ship in this release.
  - Decision owner or dedicated class: reviewer during WP-S1.
  - Evidence and decision rule: a pattern ships when an image can carry the information it loses
    AND a renderer can produce that image from available source. Everything else is catalogued and
    deferred with a reason. CSS-dependent tables and RDKit canvases are the expected first two.
- Manager/subagent decision procedure: which table rendering approach to adopt.
  - Decision owner or dedicated class: expert_coder builds, `reviewer` scores, at WP-R1.
  - Evidence and decision rule: render the full table fixture set through the smallest leading
    candidate and score it; adopt when it clears the threshold with mandatory criteria passing,
    and build a second approach only when specific criteria fail, ending at the stop rule.
    Readability rather than fidelity is the bar, so a clean redraw beats a faithful one.
- Manager/subagent decision procedure: how packaged assets such as fonts are sourced and handed to
  a renderer.
  - Decision owner or dedicated class: expert_coder during WP-R2.
  - Evidence and decision rule: whichever sourcing makes a clean-venv install render the same as
    the repo tree wins. Compare candidate faces on one fixture and keep the one that reads most
    clearly at normal Ultra display size, scored against the same rubric.
- Manager/subagent decision procedure: how source drawing options map to RDKit Python equivalents.
  - Decision owner or dedicated class: expert_coder during WP-M2.
  - Evidence and decision rule: map each option WP-S3 counted, render a fixture with and without
    it, and keep the mapping whose rendering differs in the expected way. Options with no
    equivalent are recorded rather than dropped silently.
- Manager/subagent decision procedure: which signal each selector uses.
  - Decision owner or dedicated class: expert_coder during WP-G2.
  - Evidence and decision rule: pick the signal separating the scoped fixtures from the full WP-S4
    negative sample with the fewest conditions. For tables, the `colspan`/`rowspan` plus
    `padding:0` or per-edge border rule is the starting hypothesis and stands or falls on the
    survey counts.
- Manager/subagent decision procedure: how rich alt text needs to be per pattern class.
  - Decision owner or dedicated class: reviewer during WP-S2 and WP-S3, applied by expert_coder in
    WP-B1.
  - Evidence and decision rule: judge sampled descriptions against outcome 7 -- the same
    information as the image, without leaning on the item prompt. Plain table text ships when it
    meets that bar; otherwise WP-B1 composes a pattern-aware description.
- Non-blocking follow-up: whether the text-only engines that currently decline RDKit items
  (`moodle_aiken`, `human_readable`) should accept converted items once the conversion exists.
  Revisit after the release, since their contracts are independent of this change.
- Non-blocking follow-up: whether `canvas_qti_v1_2` should also accept the switch. Canvas renders
  CSS-styled tables correctly today, and the RDKit audit notes record that its JavaScript stays
  inert, so the canvas pattern may want it even where the table pattern does not.
- Non-blocking follow-up: which catalogued-but-deferred patterns become registry entries next.
  The WP-S1 catalog carries the candidates.
- Non-blocking follow-up: whether `biology-problems/table_image_raster_lib.py` (the inverse
  data-to-table-cells approach, currently unused) should be retired now that images render in
  Ultra. That decision belongs to the sibling repo.

## Resolved decisions

These are settled by the user's explicit direction, by shipped evidence, or by evidence gathered
while planning.

- The scope is HTML compatibility remediation, not chemistry-specific rendering. Chemistry tables
  and RDKit canvases are the first two evidence-backed input classes in an extensible registry.
- Readability and preserved meaning are the acceptance standard. Reproducing Blackboard Classic,
  a browser, or the original layout is explicitly not required; a renderer may simplify layout,
  change fonts, adjust spacing, enlarge labels, or redraw content in a cleaner form. Pixel
  similarity appears nowhere in the rubric.
- Conversion applies only where a registered renderer serves a recognized pattern. Fragments
  outside the registry pass through and are reported, so the mechanism never promises to rasterize
  arbitrary broken HTML.
- The runtime stays pure Python, installed by pip alone. Rationale: this ships on PyPI as a Python
  module, so a single `pip install` stays the whole setup story.
- New dependencies are REQUIRED in `pip_requirements.txt` and `pyproject.toml`, per
  `docs/REPO_STYLE.md` and the user's explicit choice.
- The feature is off by default and enabled per run, via an engine keyword and a `bbq_converter`
  argparse flag.
- The primary design contract is one sentence: renderers consume the source representation of a
  supported fragment and produce a readable image preserving the fragment's instructional
  meaning. It covers the two shipped patterns and future ones such as SVG or MathML without
  making the mechanism chemistry-specific, and it leaves renderer capability open rather than
  assuming every fragment carries source rich enough to rebuild from.
- The registry stays a dispatch table: selector, renderer, optional metadata. Priority rules,
  versioning, capability negotiation, lifecycle hooks, and config files wait for a third renderer
  type to demonstrate the need, because two entries cannot show what a general mechanism requires.
- Table layout reconstruction and canvas redrawing stay separate renderers behind one contract.
  Combining them would force molecule drawings through a layout engine and discard the molecular
  source that makes the canvas path straightforward. Because readability is the standard, the
  table renderer is free to reconstruct a diagram directly from the parsed table rather than
  reproduce table layout at all, if that reads better.
- The canvas renderer redraws from embedded source rather than recovering pixels. Planning
  evidence: `moleculelib.py:62-73` embeds the SMILES literal, canvas id, dimensions, and
  `mdetails` options directly in the item HTML, so the source survives export. WP-S3 confirms the
  breadth of that pattern before M4 commits.
- The integration point is an engine OPTION plus a bank-level transform, following the shipped
  `canvas_src_variant` precedent. A forked engine would carry a full copy of a large engine to
  gain one boolean, and the transform living outside every engine honors the image-support plan's
  rule that engines render from a copy and leave stored item content alone.
- The transform runs BEFORE asset collection, so generated images flow through the existing
  derived media resolver with no new packaging code.
- Rubric scoring runs as a plan task over artifacts a deterministic script produced, so agent
  judgment stays outside the pytest suite.
- Charter step 1 from `docs/BLACKBOARD_ULTRA_NOTES.md` is the work here, generalized past
  chemistry. Steps 2 through 4 are already satisfied: gate D PASS (2026-07-02) proved image
  bundling works through the shipped engines.
