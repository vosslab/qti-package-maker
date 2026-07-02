# Plan: Image asset support across qti-package-maker engines

## Context

qti-package-maker converts question banks between LMS formats (BBQ text, Canvas
QTI 1.2, Blackboard QTI 2.1, Blackboard Ultra QTI 2.1, Blackboard Original
export ZIP, HTML self-test, text2qti, and other text engines). Today no engine
transports images: the shared item model
(`qti_package_maker/assessment_items/item_types.py`) has no media field, the
shared manifest builder (`common/qti_manifest.py` `create_resources_section`)
declares no `webcontent` resources, and the Ultra engine strips `<img>`
(`bb_ultra_qti_v2_1/html_sanitize.py` `drop_tags`; `compat_gate.py` hard-fails on
`<img>`). Each of the 4 zip engines hand-rolls its own `os.walk`+`zipfile` loop;
there is no shared media/zip helper.

The driving use case (user-confirmed): BBQ text files with relative `<img src>`
references are a SOURCE format. BBQ upload to Blackboard cannot carry image
binaries, so the library must read BBQ-with-images and convert to packaging
formats that can (Canvas QTI 1.2, Blackboard QTI 2.1, Blackboard Original export
ZIP, HTML self-test). The user wants maximum portability: every engine handles
images as well as its format allows, routing every one through an explicit policy path.

### Evidence summary

The user provided real, image-bearing exports of one pool under `SAMPLES/`
(2026-07-01), which pin down the per-format image contract:

- `SAMPLES/blackboard_learn_classic-qti21_export/` (model for the BB QTI 2.1 writer):
  images at package ROOT (`image-1.jpg` ...), each a `<resource type="webcontent"
  identifier="ccresNNNNN">` + `<file href>`; item resources carry
  `<dependency identifierref="ccresNNNNN"/>`; item XHTML uses real
  `<img src="../image-1.jpg" alt="">` (relative from `qti21/`), in question text
  AND inside choices. Blackboard's own basename-collision rename: `image-22(1).jpg`.
- `SAMPLES/blackboard_ultra-qti21_export/` (same pool via Ultra): every `<img>`
  degraded to `<a href="../READ_ONLY/question/_<digits>_1/embedded/image-N.jpg">`
  links; binaries under per-question `READ_ONLY/question/_<digits>_1/embedded/`;
  27 webcontent resources + dependencies. Question-id format `_<digits>_1`
  confirmed. Matches `ULTRA/image_test/`.
- `SAMPLES/blackboard_learn_classic-bb_export/` (BB Original proprietary export):
  pool dat HTML uses tokens `src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1"`;
  binaries at `csfiles/home_dir/__xid-<n>_1.jpg` with LOM sidecar `__xid-<n>_1.jpg.xml`
  mapping xid to the original course path; a `res00005.dat` CSResourceLinks entry
  per xid; the imsmanifest does NOT declare the csfiles images (implicit bundling).
  One hotspot-style file also under `res00002/<hash>/image-30.jpg`, wired via a QTI
  `<matapplication>` and tracked as a bb-namespace `<file>` in the manifest.

Real files are `.jpg`; `ULTRA/image_test/` uses `.png`. Both raster types work.
The only missing format sample is a Canvas Classic Quizzes export with an image.

Web evidence (agent-verified 2026-07-01):

- Canvas Classic Quizzes imports QTI 1.2 ZIPs with images as separate files
  declared via manifest `<resource type="webcontent">` + `<file href>`; Canvas's
  own exports use the `$IMS-CC-FILEBASE$` src token. Whether a plain relative
  `src` also resolves on import is UNCONFIRMED (gate A, highest-value probe).
- BBQ TSV upload is officially text-only; images cannot upload via BBQ (confirmed).
- Ultra does not import QTI directly (goes through Original/pools); its export
  degrades `<img>` to links. Whether a synthesized package with a
  non-server-assigned `_<digits>_1` id imports cleanly is unproven (gate D).
- text2qti supports markdown `![alt](file)` images and packages them for Canvas
  QTI 1.2 (best prior art for a text engine that carries images).
- SVG support across importers is unconfirmed/risky; PNG/JPEG/GIF are safe.

## Objectives

- The item bank owns a portable asset registry (records with a repackageable payload), with each item's references derived by scanning its HTML, usable by every engine through one shared module.
- BBQ-with-images reads cleanly and converts to Canvas QTI 1.2, Blackboard QTI 2.1, and Blackboard Original export ZIP packages whose images import into the target LMS.
- Every engine handles images predictably (bundle, verbatim reference, readable placeholder, or strict fail), routing each image through exactly one declared policy path.
- Validation fails loudly on author errors (missing files, traversal, unsupported mime) and warns on LMS-uncertain content (SVG, external URLs).
- Risky writers (Canvas src token, Ultra inline) are confirmed by real-LMS probe gates before being declared supported.

## Design philosophy

Assets are owned by a bank-level registry of portable records and derived by
scanning item HTML in one module, not tracked per engine and not stored as
mutable per-item state: two readers capture images and many writers consume
them, so per-engine scanning would duplicate the same logic many times, and a
registry (not raw bytes on every item) keeps payloads repackageable across the
read->write boundary (fix the design, not the symptom). Adopt an explicit
four-value media policy
(`package` / `reference_warn` / `placeholder_warn` / `fail`) so each engine
declares its behavior once and every path routes an image through one of the four outcomes. Resolve and
attach asset bytes at read/bank time rather than inside every item constructor,
to avoid churning the `BaseItem` API that bptools and other callers depend on.
Uncertain LMS behavior is probe-gated (long-term over short-term): no writer
claims support its target LMS has not demonstrated on a real import. Rejected
alternative: each writer parsing `<img>` itself, which would scatter dedup,
collision renaming, and validation across thirteen engines.

## Scope

- Add `qti_package_maker/common/media_assets.py`: scan HTML for `<img src>`, classify, resolve against the bank base dir, collision-safe output naming, writer-output src rewrite, optional hash dedup, and `apply_media_policy`.
- Add a bank-wide `collect_assets()` on `ItemBank` and expose per-item referenced-asset discovery without changing item constructors.
- Add a `media_policy` contract on `BaseEngine` with per-engine overrides.
- Add a shared zip/media writer so the 4 zip engines stop hand-rolling their archive loop.
- Extend `common/qti_manifest.py` to emit `webcontent` resources + per-item `<dependency>`.
- Implement image capture in both readers (`bbq_text_upload`, `blackboard_export_zip`).
- Implement image packaging in Canvas QTI 1.2, Blackboard QTI 2.1, Blackboard Original export ZIP (evidenced), and data-URI inlining in `html_selftest`; markdown image refs + copied files in `text2qti`.
- Give every remaining engine evidence-classified behavior: preserve references (bbq, human_readable, exam_yaml -- all verbatim `<img>`) or readable placeholder + warning (moodle_aiken, okla_chrst_bqgen -- markup-forbidden formats).
- Define the validation/fixture matrix (missing file, external URL, data URI, SVG, unsupported mime, basename collision, traversal, no-image regression).
- Build probe packages and manual LMS import gates (Canvas src token, BB Original import, Ultra), recording results in `docs/MEDIA_LMS_PROBES.md`.
- PNG, JPEG, GIF first-class; SVG warn-listed.

## Non-goals

- Implement audio/video/`<object>` media (reserve the asset model for later; images only).
- Build HTML-table/JS-canvas rasterization inside any engine or as part of this plan's deliverables; record it as a separate follow-up preprocessing tool (`tools/`, likely Playwright) that maps ItemBank -> ItemBank, since engines must not mutate item content and JS never survives QTI import.
- Ship Ultra inline-image writing before the Ultra probe demonstrates a working pattern; until then Ultra uses `placeholder_warn` (readable placeholder + itemized warning + documented limitation, strict-fail flag preserved).
- Target Canvas New Quizzes image import (documented-unreliable).
- Emit uploadable image files into text-only outputs (BBQ, Aiken, okla, YAML); those preserve references or placeholders and warn.
- Support SVG as first-class (warn-listed only) or embed external `http(s)` URLs into packages.
- Normalize item CRC identity against image paths (this plan keeps the same image at two paths as two identities; documented as a known limitation).

## Current state summary

- Item model: `BaseItem` fields are text-only; images survive only as inline HTML strings in `question_text`/choices (`assessment_items/item_types.py`).
- Shared manifest: `common/qti_manifest.py create_resources_section` emits only item XML + `assessment_meta.xml` resources; single extension point for both QTI writers.
- Zip assembly: duplicated `os.walk`+`zipfile`+`relpath`+`rmtree` per zip engine; no shared helper.
- Engine media behavior today: `bbq_text_upload` passes HTML verbatim; `bb_ultra_qti_v2_1` strips `<img>` and hard-fails; `blackboard_export_zip` writes empty `csfiles/`; all others ignore images.
- Registry (`engines/engine_registration.py`) auto-detects read/write; no media capability column.
- Samples on hand: `ULTRA/image_test/` plus the `SAMPLES/` triple. Readers today: bbq_text_upload, blackboard_export_zip, okla_chrst_bqgen, text2qti. `exam_yaml` exists in code (`write_item.py` verified: `question_text` -> YAML `statement` verbatim) though `docs/ENGINES.md` omits it; WS-DOCS fixes that stale row.

## Architecture boundaries and ownership

- `common/media_assets.py` (NEW): file-reference-first. Items keep the author's plain `<img src="images/foo.jpg" alt="...">`; there is no `asset:` scheme in item content. A `MediaAsset` is a DERIVED resolution result (not durable state) produced by scanning an item's HTML and resolving each `src` against the bank `media_base_dir`: it carries original src, kind (local / external / data-uri), MIME, the resolved file path, the collision-safe output filename a writer will use, and an optional content hash used only for dedup/collision/verification (not identity). Functions: `scan_html_for_assets` (finds `<img src>` in a field), `resolve_asset(src, base_dir)` (-> record), `rewrite_html_srcs(html, fn)` (used ONLY on writer output, mapping in-content src -> the writer's platform path), collision-safe output naming, `apply_media_policy`. Single owner of scan/rewrite logic. Consistent warnings: `apply_media_policy` is the one place external-URL, data-URI, and SVG warnings are emitted (itemized), so every engine surfaces them the same way.
- `common/zip_writer.py` (NEW): build a zip from an {archive_path: bytes|src_path} map including explicit empty dirs (e.g. `csfiles/`); the 4 zip engines call it.
- `assessment_items/item_bank.py`: the `ItemBank` owns `media_base_dir` and the media-resolution policy -- resolution is otherwise PURELY DERIVED. `collect_assets()` scans every item's HTML fields at collect/export time and resolves each `<img src>` against `media_base_dir` into a package-ready record (original src, MIME, resolved file path, collision-safe output name) computed fresh each call -- no durable per-asset registry for file-backed assets. The ONLY persisted state is retained payloads that have no re-resolvable source: an imported-ZIP reader extracts binaries to a directory, points `media_base_dir` at that directory, and rewrites the item HTML to relative paths under it -- so an imported package becomes the SAME shape as file-authored input and flows through the identical derived resolver; the extraction dir (a directory lifetime) is the retention, not a parallel registry. An explicit `add_image(src, bytes)` with no file spills to a temp file under `media_base_dir` to keep one uniform derived path. WHICH images an item references is derived by the scan, never persisted as mutable item state, so item constructors and the `BaseItem` API stay unchanged (no bptools churn).
- `engines/base_engine.py`: `media_policy` class attribute with four values -- `package` (bundle files + rewrite src), `reference_warn` (keep the image reference verbatim + itemized warning that files are not transported), `placeholder_warn` (format carries no markup; substitute a readable placeholder like `[image: figure.png]` + itemized warning), `fail` (raise; Ultra strict). Every policy routes an image through one of these four outcomes. Default `reference_warn` (safest: preserves the reference verbatim and defers bundling).
- Ultra compat gate stays the last line of defense; shared policy replaces `<img>` with a placeholder before the gate fires, so the gate stays silent in normal operation.

### Per-engine image outcome (evidence-based, maximum-portability default)

| Engine | Policy | Confirmed contract |
| --- | --- | --- |
| canvas_qti_v1_2 | package | Images in `media/`; inline `<img>` in `text/html` mattext; `webcontent` resource + dependency. Src token (relative vs `$IMS-CC-FILEBASE$`) decided at gate A; both variants buildable |
| blackboard_qti_v2_1 | package | Root-level `image-N.jpg` + `webcontent` + item `<dependency>` + `<img src="../image-N.jpg">` (per `SAMPLES/blackboard_learn_classic-qti21_export`) |
| blackboard_export_zip | package (write) | Real mechanism per `SAMPLES/blackboard_learn_classic-bb_export`: file at `csfiles/home_dir/__xid-<n>.jpg` + `.jpg.xml` LOM sidecar + `res00005.dat` CSResourceLinks entry + body `@X@...bbcswebdav/xid-<n>` token (manifest-untracked); hotspot via QTI `<matapplication>` (manifest-tracked). Evidenced now; ships on sample + roundtrip evidence, sandbox import is optional gate-B verification |
| html_selftest | package | Emits an mkdocs-material HTML FRAGMENT (`<div class="qti-selftest">`, not a standalone doc); images inlined as base64 `data:` URIs so the fragment is location-independent at any nav depth. Existing `.qti-selftest img { max-width:100%; height:auto }` (`html_functions.py`) already renders them responsively in light/slate |
| bb_ultra_qti_v2_1 | placeholder_warn -> package | Default placeholder+warn; upgrades to `READ_ONLY/question/_<digits>_1/embedded/` + `<a href>` + dependency only if gate D import confirms |
| bbq_text_upload | reference_warn | Source bridge: keep `<img>` verbatim + itemized upload warning |
| human_readable | reference_warn | Keep reference readable (name + alt + source path) |
| text2qti | reference_warn | Emit markdown `![alt](media/name.png)` + copy files beside output (its reader round-trips the token) |
| okla_chrst_bqgen | placeholder_warn | Readable placeholder + warning (its reader round-trips the token) |
| moodle_aiken | placeholder_warn | Aiken is strict plain-text (cited); readable placeholder + warning |
| exam_yaml | reference_warn | Decided from code: `write_item.py:23,29` emits `question_text` verbatim into the YAML `statement` field, so `<img>` HTML carries through unchanged. Verbatim reference + itemized warning; write-only engine, no machine round-trip claim. (Engine exists in code though `docs/ENGINES.md` omits it -- stale doc, fix in WS-DOCS) |

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Expected patches |
| --- | --- | --- |
| M0 / WS-CORE | common/media_assets.py, common/zip_writer.py, item_bank.py, base_engine.py | 2-3 |
| M0 / WS-CORE-TEST | tests/unit/test_media_assets.py, fixture assets | 1-2 |
| M1 / WS-QTI | common/qti_manifest.py, canvas_qti_v1_2/, blackboard_qti_v2_1/ | 2-3 |
| M1 / WS-READERS | bbq_text_upload/read_package.py, blackboard_export_zip/read_package.py | 2 |
| M1 / WS-BBEXPORT-WRITE | blackboard_export_zip/ (csfiles embedding, sidecar, CSResourceLinks, pool dat refs) | 1-2 |
| M1 / WS-TEXT | html_selftest/, text2qti/, bbq/write_item.py, reference/placeholder engines | 2-3 |
| M1 / WS-TESTS | tests/integration/ additions, roundtrip tests | 1-2 |
| M2 / WS-PROBES | devel/ probe builders, docs/MEDIA_LMS_PROBES.md | 1-2 |
| M2 / WS-ULTRA | bb_ultra_qti_v2_1/ (only if gate D passes) | 0-2 |
| all / WS-DOCS | docs/ENGINES.md, ENGINE_AUTHORING.md, FORMATS.md, CHANGELOG.md, README | 1-2 |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M0 | Core asset model | Shared media module + zip writer, bank asset plumbing, engine policy contract | Every item knows its images; every engine declares a policy |
| M1 | Engine image support | Full-render targets (Canvas, BB 2.1, BB Original, HTML self-test), reference/placeholder behavior in every text engine, reader capture, tests | Image-bearing banks convert predictably through every engine in one version |
| M2 | LMS probes and Ultra decision | Manual import gates on real LMSes; Ultra pattern decided by evidence; probe docs | Support claims backed by real imports |

### Milestone: M0 core asset model

- Depends on: none
- Workstreams: WS-CORE, WS-CORE-TEST
- Entry criteria: none
- Exit criteria: `MediaAsset` API + four `media_policy` values frozen and documented in module docstrings; `common/zip_writer.py` builds zips (empty dirs supported) and the 4 zip engines call it with behaviorally-equivalent no-image output (same required files, same parsed XML structure, same item content, same import-relevant paths); `pytest tests/unit/test_media_assets.py` green; full `pytest tests/` green (no regressions). Obvious follow-ons: fix pyflakes/typing gates, `docs/CHANGELOG.md` entry.
- Parallel-plan ready: yes (WS-CORE and WS-CORE-TEST run concurrently once the WP-C1 API sketch lands; max 2-3 doers)

### Milestone: M1 engine image support

- Depends on: M0 (asset model + zip writer are the interfaces every lane consumes)
- Workstreams: WS-QTI, WS-READERS, WS-BBEXPORT-WRITE, WS-TEXT, WS-TESTS, WS-DOCS
- Entry criteria: M0 exit criteria met
- Exit criteria: fixture matrix green; full-render targets (BBQ-with-images -> Canvas ZIP, BB 2.1 ZIP, BB Original ZIP) each contain the image file, rewritten src, and correct manifest/dat declarations; reference-preserving engines keep refs verbatim with itemized warnings; placeholder engines emit readable placeholders with a cited format justification; read->write roundtrip through blackboard_export_zip preserves the image bytes; every engine's behavior with an image-bearing bank has at least one test. Obvious follow-ons: update `show_available_engines()` media column, changelog per patch, rerun full `pytest tests/`.
- Parallel-plan ready: yes (WS-QTI, WS-READERS, WS-BBEXPORT-WRITE, WS-TEXT are independent lanes over disjoint engine dirs; WS-TESTS consumes their interfaces; max 6 doers)

### Milestone: M2 LMS probes and Ultra decision

- Depends on: M1 (probe packages are built by the new writers)
- Workstreams: WS-PROBES, WS-ULTRA
- Entry criteria: M1 met; Canvas + Blackboard/Ultra sandbox access (manager runs probes directly when it has access, else emits exact user-facing probe instructions)
- Exit criteria: results recorded in `docs/MEDIA_LMS_PROBES.md` for the two FORMAL gates -- gate A (Canvas src token variant) and gate D (Ultra synthesized-id import); Ultra either implements the demonstrated pattern (compat gate downgrades `<img>` to policy-managed) or documents placeholder-plus-warn as final with rationale. Gate B (BB Original import of the generated image ZIP) is OPTIONAL verification, not a blocker: the BB Original writer is fully evidenced by `SAMPLES/blackboard_learn_classic-bb_export` and proven by the in-code write->read roundtrip (WP-B1) plus the automated structure check, so it ships on that evidence; a sandbox import result is recorded when convenient. Obvious follow-ons: update `docs/ENGINES.md` support table from outcomes, changelog.
- Parallel-plan ready: yes (probe kits independent per LMS; imports are user-serial but prep parallelizes; max 2 doers plus gates)

## Workstream breakdown

### Workstream: WS-CORE

- Owner: expert_coder (design-sensitive: the API everything consumes)
- Needs: evidence in this plan; existing zip-engine loops
- Provides: `MediaAsset`, scan/rewrite/dedup/policy, `common/zip_writer.py`, `ItemBank.collect_assets()`, `BaseEngine.media_policy`
- Expected patches: 2-3

### Workstream: WS-CORE-TEST

- Owner: tester
- Needs: WS-CORE API sketch (WP-C1)
- Provides: unit tests that generate tiny image bytes INLINE (small base64 constants in the test module written to `tmp_path`), following the PYTEST_STYLE fixture policy (inline setup first). The BBQ reader case is also built in `tmp_path`. The only committed durable artifact across the whole plan is one `real-export` slice (1-2 questions) trimmed from `SAMPLES/blackboard_learn_classic-bb_export`, kept because its proprietary multi-file shape is the behavior under test
- Expected patches: 1-2

### Workstream: WS-QTI

- Owner: coder
- Needs: M0 API; fixtures; `SAMPLES/blackboard_learn_classic-qti21_export`
- Provides: webcontent + `<file>` + `<dependency>` in `qti_manifest.py`; media copying + src rewrite in canvas_qti_v1_2 and blackboard_qti_v2_1; both Canvas src variants selectable for gate A
- Expected patches: 2-3

### Workstream: WS-READERS

- Owner: coder
- Needs: M0 API; `SAMPLES/blackboard_learn_classic-bb_export`
- Provides: bbq reader resolving relative `src` against the input dir; blackboard_export_zip reader extracting both mechanisms (csfiles `__xid` via body token + CSResourceLinks; hotspot `<matapplication>`)
- Expected patches: 2

### Workstream: WS-BBEXPORT-WRITE

- Owner: expert_coder (proprietary format; design directly from the sample)
- Needs: M0 API; `SAMPLES/blackboard_learn_classic-bb_export`
- Provides: csfiles/home_dir embedding, `@X@` token minting, `.jpg.xml` LOM sidecars, `res00005.dat` CSResourceLinks entries, deterministic layout
- Expected patches: 1-2

### Workstream: WS-TEXT

- Owner: coder
- Needs: M0 API
- Provides: html_selftest base64 data URIs; text2qti `![alt](media/name.png)` + copied files; bbq verbatim `<img>` + upload warning; human_readable reference preservation; placeholders + citations for moodle_aiken/okla_chrst_bqgen; exam_yaml verbatim `<img>` in YAML `statement` + warning (decided)
- Expected patches: 2-3

### Workstream: WS-TESTS

- Owner: tester
- Needs: interfaces from WS-QTI, WS-READERS, WS-BBEXPORT-WRITE, WS-TEXT
- Provides: integration tests per fixture matrix; roundtrip additions; no-image byte/behavior-identical regression
- Expected patches: 1-2

### Workstream: WS-PROBES

- Owner: coder (kits), manager/user (imports)
- Needs: M1 writers
- Provides: `devel/` probe builders (Canvas both-variant ZIPs; BB Original image ZIP from WP-B1; Ultra kit replicating the `SAMPLES/blackboard_ultra-qti21_export` a-href pattern plus an `<img>` variant); `docs/MEDIA_LMS_PROBES.md` results log
- Expected patches: 1-2

### Workstream: WS-ULTRA

- Owner: expert_coder
- Needs: gate D result from WS-PROBES
- Provides: Ultra image pattern if the probe demonstrates one, else documented placeholder-plus-warn finality
- Expected patches: 0-2

### Workstream: WS-DOCS

- Owner: planner
- Needs: outcomes per milestone
- Provides: docs/ENGINES.md media column, ENGINE_AUTHORING.md media-policy section, FORMATS.md, README table, changelog
- Expected patches: 1-2

## Work packages

### Work package: WP-C1 media_assets module + policy freeze

- Owner: expert_coder
- Touch points: `common/media_assets.py` (new)
- Depends on: none
- Acceptance criteria: `MediaAsset` is a portable record keyed by the in-content src (original src, kind, MIME, lazy payload as resolvable path or bytes, collision-safe output name, optional hash) that repackages from either a file path or in-memory/extracted bytes; item content keeps the author's plain `<img src>` (no `asset:` scheme); scan finds `<img src>` in arbitrary item HTML via lxml (mirroring `validator.validate_html`); classifies local/external/data-uri; missing local file raises with the filename; `../` traversal escaping the base dir raises; unsupported mime (e.g. `.webp`) raises; PNG/JPEG/GIF first-class, SVG packaged with a warning; deterministic collision-safe output name preserving path identity (`images/foo.png` and `figures/foo.png` do not collide); an optional content hash supports dedup/collision/verification but is not the identity; `rewrite_html_srcs` (writer output only) maps in-content src to the writer's platform path; `apply_media_policy` implements `package`/`reference_warn`/`placeholder_warn`/`fail` with itemized warnings, routing every image through exactly one of the four outcomes.
- Verification commands: `source source_me.sh && pytest tests/unit/test_media_assets.py`
- Obvious follow-ons: module docstring documents the frozen API; changelog.

### Work package: WP-C2 zip writer, bank plumbing, engine policy

- Owner: expert_coder
- Touch points: `common/zip_writer.py` (new), `assessment_items/item_bank.py`, `engines/base_engine.py`, the 4 zip engines' `engine_class.py`
- Depends on: WP-C1
- Acceptance criteria: `zip_writer` builds a zip from an {archive_path: bytes|src_path} map incl. explicit empty dirs; the 4 zip engines call it with behaviorally-equivalent no-image output (structure-focused assertions, not raw bytes -- ZIP metadata/order makes raw bytes brittle); `ItemBank` owns `media_base_dir` + media-resolution policy; `collect_assets()` returns package-ready records plus per-item dependency data by scanning each item's HTML and resolving each `src` against `media_base_dir` at collect/export time (purely derived, recomputed each call, no durable per-asset registry); the only retained state is the extraction dir a ZIP reader points `media_base_dir` at (and a temp file for `add_image(src, bytes)`); per-item referenced assets are derived on scan, never persisted as mutable state, so item constructors and the `BaseItem` API are unchanged; `BaseEngine.media_policy` defaults to `reference_warn`; full suite green.
- Verification commands: `source source_me.sh && pytest tests/`
- Obvious follow-ons: fix typing/pyflakes fallout; changelog.

### Work package: WP-T1 inline unit tests

- Owner: tester
- Touch points: `tests/unit/test_media_assets.py` (new)
- Depends on: WP-C1
- Acceptance criteria: matrix rows 1-8 covered; image bytes generated INLINE from small base64 constants in the test module written to `tmp_path` (a minimal valid PNG and GIF are each under ~70 bytes; JPEG and SVG constants likewise tiny), following the PYTEST_STYLE fixture policy -- no committed image files for the unit layer. The collision case uses two distinct inline byte constants under the same basename; the `.webp`-reject case uses an inline constant with a `.webp` name.
- Verification commands: `source source_me.sh && pytest tests/unit/test_media_assets.py`
- Obvious follow-ons: reuse the same inline byte helpers in integration; changelog.

### Work package: WP-Q1 shared manifest webcontent

- Owner: coder
- Touch points: `common/qti_manifest.py`
- Depends on: WP-C2
- Acceptance criteria: `create_resources_section` accepts an asset list and emits one `<resource type="webcontent">` + `<file href>` per asset plus a `<dependency identifierref>` on each referencing item resource; shared assets produce one resource with multiple dependencies (pattern matches `SAMPLES` QTI 2.1 + `ULTRA/image_test`); old signature keeps working until both writers migrate this milestone.
- Verification commands: `source source_me.sh && pytest tests/ -k manifest`
- Obvious follow-ons: both QTI writers consume the new signature; changelog.

### Work package: WP-Q2 Canvas + Blackboard QTI writers

- Owner: coder
- Touch points: `engines/canvas_qti_v1_2/`, `engines/blackboard_qti_v2_1/`
- Depends on: WP-Q1
- Acceptance criteria: images copied into the ZIP; src rewritten -- Canvas exposes both variants (relative and `$IMS-CC-FILEBASE$`) for gate A; BB 2.1 matches `SAMPLES/blackboard_learn_classic-qti21_export` (root images, `<img src="../image.ext">`, `ccresNNNNN` webcontent, per-item `<dependency>`); collision renames deterministic; ZIP-inspection test passes. Canvas fallback if gate A inconclusive: ship QTI-1.2 spec-relative packaging with a documented manual-import check rather than blocking Canvas.
- Verification commands: `source source_me.sh && pytest tests/ -k "canvas or blackboard_qti"`
- Obvious follow-ons: probe-builder hook for WS-PROBES; changelog.

### Work package: WP-R1 bbq reader capture + writer warning

- Owner: coder
- Touch points: `engines/bbq_text_upload/read_package.py`, `write_item.py`
- Depends on: WP-C2
- Acceptance criteria: the reader sets the bank `media_base_dir` to the input file's directory so relative `src` (e.g. `images/foo.jpg`) resolves purely by derivation (no attached per-item state); missing file raises with the filename; writer keeps `<img>` verbatim and prints an itemized warning that BBQ upload cannot carry image files.
- Verification commands: `source source_me.sh && pytest tests/ -k bbq`
- Obvious follow-ons: reuse bbq fixture in roundtrip tests; changelog.

### Work package: WP-R2 blackboard_export_zip reader capture

- Owner: coder
- Touch points: `engines/blackboard_export_zip/read_package.py`
- Depends on: WP-C2
- Acceptance criteria: body `@X@...bbcswebdav/xid-<n>_1` tokens resolved to `csfiles/home_dir/__xid-<n>_1.<ext>` binaries (cross-checked against `res00005.dat` CSResourceLinks), original filename recovered from the LOM `.jpg.xml` sidecar; hotspot `<matapplication uri>` files read from `res00002/<hash>/`; the reader extracts binaries into a directory, sets the bank `media_base_dir` to that directory, and rewrites the item HTML to plain relative `<img src="<recovered-name>">` under it -- so the imported ZIP becomes the SAME shape as file-authored input and flows through the identical derived resolver (this is how imported-ZIP assets stay available for repackaging); zip-safety precedent respected (no traversal writes). Fixture trimmed from `SAMPLES/blackboard_learn_classic-bb_export`.
- Verification commands: `source source_me.sh && pytest tests/ -k "blackboard_export and read"`
- Obvious follow-ons: roundtrip with WP-B1; changelog.

### Work package: WP-B1 blackboard_export_zip image write (evidenced, complex)

- Owner: expert_coder
- Touch points: `engines/blackboard_export_zip/engine_class.py`, `assessment_meta.py`
- Depends on: WP-C2; `SAMPLES/blackboard_learn_classic-bb_export`
- Acceptance criteria: reproduce the confirmed mechanism -- write the file to `csfiles/home_dir/__xid-<n>.jpg`, emit the body `@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>` token, write the `.jpg.xml` LOM sidecar, add the matching `res00005.dat` CSResourceLinks entry, mint unique xids, leave csfiles manifest-untracked (as in the sample); hotspot images use the QTI `<matapplication>` + manifest `<file>` path; in-code write->read roundtrip preserves bytes and refs. Split the xid-token/CSResourceLinks wiring into its own reviewable step given the complexity.
- Verification commands: `source source_me.sh && pytest tests/integration/test_blackboard_export_zip_roundtrip.py`
- Obvious follow-ons: optional gate-B verification probe package; changelog.

### Work package: WP-X1 text + html engines

- Owner: coder
- Touch points: `engines/html_selftest/`, `engines/text2qti/`, `engines/human_readable/`, `engines/moodle_aiken/`, `engines/okla_chrst_bqgen/`, `engines/exam_yaml/`
- Depends on: WP-C2
- Acceptance criteria: html_selftest resolves each `<img src>` through `media_assets`, reads the bytes, and rewrites src to a base64 `data:<mime>;base64,...` URI (via `rewrite_html_srcs` on writer output only) so the emitted fragment has zero external refs and embeds cleanly at any mkdocs-material nav depth; MIME comes from the `MediaAsset` record; the existing `.qti-selftest img` responsive CSS is left unchanged (no new CSS needed); a test asserts the output fragment contains `data:image/png;base64,` and no `src="images/`. text2qti emits `![alt](media/name.png)` + copies files beside output; human_readable keeps refs readable (name + alt + source path); moodle_aiken + okla_chrst_bqgen emit `[image: name.ext]` placeholders + itemized warnings, each with a one-line format citation in the engine docstring; exam_yaml keeps `<img>` verbatim in its YAML `statement` strings + itemized warning (decided from `write_item.py:23,29` evidence; also fix its missing row in `docs/ENGINES.md`). Reader-backed engines (text2qti, okla) emit a readable reference their own reader re-resolves to a `MediaAsset` record (no `asset:` scheme in content).
- Verification commands: `source source_me.sh && pytest tests/test_all_engines.py`
- Obvious follow-ons: `show_available_engines()` media column; changelog.

### Work package: WP-T2 integration + roundtrip tests

- Owner: tester
- Touch points: `tests/integration/` additions
- Depends on: WP-Q2, WP-R1, WP-R2, WP-B1, WP-X1
- Acceptance criteria: integration matrix rows 8-13 covered; BBQ-with-images -> each packaging engine end-to-end (BBQ input built in `tmp_path`); no-image regression (row 12) proves behavior-identical output; the BB Original roundtrip (row 9) uses the trimmed `real-export` slice.
- Verification commands: `source source_me.sh && pytest tests/`
- Obvious follow-ons: changelog.

### Work package: WP-P1 probe kits + results doc

- Owner: coder (kits), manager/user (imports)
- Touch points: `devel/` probe scripts (new), `docs/MEDIA_LMS_PROBES.md` (new)
- Depends on: WP-Q2, WP-B1
- Acceptance criteria: gate A kit (Canvas relative-src and `$IMS-CC-FILEBASE$` variants); optional gate-B kit (generated BB Original image ZIP for convenience verification); gate D kit (Ultra a-href pattern replicating `SAMPLES/blackboard_ultra-qti21_export` with a synthesized `_<digits>_1` id, plus an `<img>` variant); an AUTOMATED structure test unzips each probe package and asserts its layout/manifest matches the corresponding `SAMPLES/` reference BEFORE any human import, so package correctness is proven by fixtures and only real-LMS rendering waits on a sandbox; results template ready to fill after sandbox imports.
- Verification commands: `source source_me.sh && python3 devel/<script>.py` runs clean
- Obvious follow-ons: record results, update docs/ENGINES.md claims; changelog.

### Work package: WP-U1 Ultra decision + implementation

- Owner: expert_coder
- Touch points: `engines/bb_ultra_qti_v2_1/` (engine_class, html_sanitize, compat_gate)
- Depends on: WP-P1 gate D result
- Acceptance criteria: if a probe pattern renders in Ultra, implement it (asset under `READ_ONLY/question/_<digits>_1/embedded/`, `<a href>`, webcontent + dependency) and downgrade the compat gate `<img>` hard-fail to policy-managed; else document placeholder-plus-warn as final in `docs/BLACKBOARD_ULTRA_NOTES.md` with probe evidence.
- Verification commands: `source source_me.sh && pytest tests/ -k ultra`
- Obvious follow-ons: changelog; ENGINES.md update.
- **Status: EXECUTED 2026-07-02; gate D RE-OPENED by control evidence
  2026-07-02.** Gate D first ran on the real Blackboard Ultra SaaS sandbox;
  all three import paths (QTI 2.1 `<a href>`, QTI 2.1 `<img>`, `bb_export`
  conversion) showed no image after import while the question itself
  imported cleanly. The "else" branch was applied: `placeholder_warn` was
  documented as final in `docs/BLACKBOARD_ULTRA_NOTES.md` with probe
  evidence, and no compat-gate or engine code change was made since
  `placeholder_warn` was already the shipped default and the strict-fail
  flag is preserved. That "final" conclusion is now retracted: the same day,
  a control import of `control_ultra-qti21.zip` (a faithful re-zip of
  Blackboard's own real Ultra export, built by
  `devel/build_sample_control_zips.py`, no writer code of ours involved)
  rendered its image inline in the same sandbox, and the two Learn
  `B-control` re-zips rendered theirs too. This proves there is no LMS
  ceiling on media; the "if" branch (implement the demonstrated pattern) is
  back in play pending a root-cause investigation into the package-shape
  delta between our writers' output and Blackboard's own export
  (`docs/active_plans/audits/media_import_delta_report.md`, in progress).
  `placeholder_warn` stays the shipped default until that investigation
  lands a fix. See `docs/MEDIA_LMS_PROBES.md` for the gate B and gate D
  results tables and `docs/BLACKBOARD_ULTRA_NOTES.md` "Final status" for the
  corrected framing.
- **Final status (2026-07-02): WP-U1 superseded; the Ultra engine was
  removed instead of upgraded.** The root-cause investigation concluded
  with gate D PASS (visible-figure round): the earlier "no image after
  import" reading was a false negative caused by an invisible 1x1-pixel
  probe figure, and packaged images render in Ultra on every import path
  once real writer bugs were fixed. With that confirmed, the "if" branch's
  `package` media policy upgrade for a dedicated Ultra engine was not
  implemented; instead, per user directive, the entire
  `qti_package_maker/engines/bb_ultra_qti_v2_1/` engine and its 4 dedicated
  test files were deleted as redundant, because `blackboard_qti_v2_1`
  ("Import from QTI 2.1 package") and `blackboard_export_zip` ("Import from
  file", which also carries Matching) already cover every case the WP-U1
  upgrade would have added. See `docs/CHANGELOG.md`'s 2026-07-02 entry
  ("Decisions and Failures") and `docs/ENGINES.md`'s "Blackboard Ultra
  support" section for the current guidance.

### Work package: WP-D1 documentation close-out

- Owner: planner
- Touch points: `docs/ENGINES.md`, `docs/ENGINE_AUTHORING.md`, `docs/FORMATS.md`, `README.md`, `docs/CHANGELOG.md`
- Depends on: WP-X1 (M1 close), WP-U1 (M2 close)
- Acceptance criteria: per-engine media behavior table published; ENGINE_AUTHORING.md documents the media_policy contract for new engines; markdown-links test green.
- Verification commands: `source source_me.sh && pytest tests/test_markdown_links.py`
- Obvious follow-ons: none.

## Acceptance criteria and gates

- Per-patch gate: `source source_me.sh && pytest tests/test_pyflakes_code_lint.py tests/test_function_typing.py` plus the patch's targeted tests; tabs, no try/except, explicit key access per `docs/PYTHON_STYLE.md`.
- Integration gate (M1): fixture matrix fully green; BBQ-with-images converts to Canvas, BB 2.1, and BB Original ZIPs containing the image with correct declarations; roundtrip preserves bytes; no-image outputs behavior-identical to pre-plan.
- Manual review gate (M2): the two formal probes import into Canvas Classic (gate A) and the Ultra sandbox (gate D); images render (or the Ultra verdict is recorded) in `docs/MEDIA_LMS_PROBES.md`. The Blackboard Original import is optional verification (writer is sample-evidenced); record its result when performed. Doc support claims may not exceed probe evidence.
- Human-gate fallback (no hidden human dependency): every engineering deliverable -- all writers, readers, tests, and probe kits -- completes on fixtures and automated structural assertions WITHOUT waiting for a human import. The automated proof unzips each generated package and asserts its manifest resource/dependency/file layout matches the corresponding `SAMPLES/`-derived expected pattern (BB QTI 2.1 and Ultra directly from `SAMPLES/`; Canvas from the QTI-1.2 spec + text2qti prior art until a real Canvas sample exists). Human imports only flip documented support claims and the Ultra `placeholder_warn -> package` upgrade; nothing else blocks on them.

## Test and verification strategy

Fixture policy (per the PYTEST_STYLE fixture policy -- inline setup first). Every row is classified by Kind:

- `inline` -- item bank built in the test; image bytes from small base64 constants written to `tmp_path`; no committed file.
- `file-shape` -- a tiny durable file whose shape/loader is the behavior under test.
- `real-export` -- a trimmed 1-2 question slice of a real `SAMPLES/` export (preserves the real file contract without a synthetic fixture set).
- `probe` -- a package generated at run time by a `devel/` script, its structure asserted against a `real-export` reference.

The only committed durable artifact is one `real-export` slice of `SAMPLES/blackboard_learn_classic-bb_export` (row 9); everything else is `inline` or generated. The BBQ case (row 8) is constructed in `tmp_path` (a small `.txt` plus inline image bytes) rather than committed, since the reader's relative-path resolution -- not any particular committed tree -- is what it proves.

Unit cases (WS-CORE-TEST / WP-T1):

| # | Case | Kind | Expected |
| --- | --- | --- | --- |
| 1 | MC item with a local PNG in question_text AND inside a choice | inline | scanned from all HTML fields, packaged once, src rewritten, manifest entry |
| 2 | Two items, identical image bytes | inline | one packaged file, both srcs point at it (dedup) |
| 3 | Same basename, different bytes | inline | deterministic rename, both packaged |
| 4 | External https URL | inline | untouched, not packaged, warn on package engines |
| 5 | data: URI | inline | html_selftest passes; packaging QTI engines raise (author must supply a file to bundle) |
| 6 | SVG | inline | packaged with a warning |
| 7 | Error inputs: missing local file, `.webp` mime, `../` traversal escaping base dir | inline | each raises with a clear message naming the offending src |

Integration cases (WS-TESTS / WP-T2):

| # | Case | Kind | Expected |
| --- | --- | --- | --- |
| 8 | BBQ .txt with relative img + sibling dir (built in `tmp_path`) | inline | reader sets media_base_dir; src resolves |
| 9 | BB Original ZIP with csfiles image | real-export | reader extracts; write->read roundtrip preserves bytes + refs |
| 10 | Ultra image item: default policy, then strict flag | inline | default -> readable placeholder + warning, compat gate silent; strict -> raises |
| 11 | html_selftest with an image | inline | every `src` is a `data:` URI, zero external refs |
| 12 | No-image bank through every engine | inline | behavior-identical to current output |
| 13 | Image item -> reference engines (bbq, human_readable, text2qti, exam_yaml) vs placeholder engines (moodle_aiken, okla_chrst_bqgen) | inline | reference engines keep the ref verbatim + warn; placeholder engines emit `[image: name.ext]` + warn |

Probe packages (WS-PROBES / WP-P1) are Kind `probe`: generated at run time (Canvas both-variant ZIPs, Ultra a-href + `<img>` kit, optional BB Original ZIP) and asserted against `real-export` structure references trimmed from `SAMPLES/` before any human import.

Commands: `pytest tests/unit/test_media_assets.py`, `pytest tests/test_all_engines.py`, `pytest tests/ -k roundtrip`, full `pytest tests/`. Manual: probe imports per gate table.

## Migration and compatibility policy

- Additive rollout: `media_policy` defaults to `reference_warn` (keeps HTML untouched -- matches today's pass-through, upgrades silent behavior with warnings); the manifest helper keeps its old signature until both QTI writers migrate within M1; the asset store is empty by default.
- Backward compatibility: no-image banks produce behavior-identical outputs (tested, row 12); bptools and downstream callers need no changes (no item-constructor churn).
- Legacy deletion criteria: the Ultra compat_gate `<img>` hard-fail is removed only after WP-U1 lands a working pattern; otherwise retained under the strict flag.
- Rollback strategy: each lane touches a disjoint engine dir; reverting a lane's patches restores current behavior without affecting others; the shared layer stays inert behind the empty asset store.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Canvas ignores plain relative src | Canvas images 404 on import | Gate A variant 1 fails | coder + user | Ship both src variants; adopt whichever renders; spec-relative fallback documented |
| Synthesized Ultra `_<digits>_1` id may not import | Ultra image write invalid | Gate D fails | expert_coder | Ultra stays placeholder_warn (no forged write); rasterization tool becomes the practical path (follow-up) |
| bb_export write is a complex multi-file mechanism | Partial wiring rejected on import | WP-B1 integration | expert_coder | Fully evidenced in `SAMPLES/`; mirror exactly; split xid/CSResourceLinks into its own step; in-code roundtrip + automated structure check are the ship gate, optional sandbox import is bonus verification |
| base_dir/asset plumbing churns downstream API | bptools caller breakage | item-constructor change | expert_coder | Compute referenced assets by scan at bank/read time, not in constructors; full-suite regression |
| Optional hash-dedup merges distinct images | Wrong image reused | hash collision / same bytes different intent | expert_coder | Hash is an optional aid, not identity; registry keyed by in-content src, so dedup only merges identical bytes; make dedup opt-in and verifiable |
| Scope creep into audio/video/rasterizer | Milestones balloon | reviewer sees non-image or rasterizer work | reviewer | Non-goal fence; rasterizer is a separate follow-up tool |

## Rollout and release checklist

- [ ] M0 merged; zip writer behavior-equivalent; full suite green; changelog
- [ ] M1 merged; fixture matrix green; no-image regression proven; every engine has a media policy
- [ ] Probe kits delivered; formal gates A and D executed in sandboxes; BB Original import verified when convenient (optional)
- [ ] `docs/MEDIA_LMS_PROBES.md` records all gate results (including failures)
- [x] Ultra verdict implemented or documented (WP-U1) -- documented as final,
      2026-07-02, see `docs/BLACKBOARD_ULTRA_NOTES.md`
- [ ] docs/ENGINES.md media column matches probe evidence exactly
- [ ] Version bump per CalVer; release notes mention per-engine image support

## Documentation close-out requirements

- Active plan / progress tracker: mirror to `docs/active_plans/active/image_support_plan.md` at dispatch; `git mv` to `docs/archive/` at close.
- docs/CHANGELOG.md entry: one per patch, "Patch N: [component] [intent]"; record probe outcomes (incl. failures) under Decisions and Failures.
- Archive / closure notes: gate results + Ultra verdict summarized in `docs/BLACKBOARD_ULTRA_NOTES.md` and `docs/MEDIA_LMS_PROBES.md`; update `docs/FORMATS.md`/`docs/ENGINES.md` capability tables.

## Patch plan and reporting format

- Patch 1: media_assets module + policy freeze (WP-C1)
- Patch 2: zip writer + bank plumbing + engine policy (WP-C2)
- Patch 3: unit tests + fixtures (WP-T1)
- Patch 4: shared manifest webcontent (WP-Q1)
- Patch 5: Canvas + Blackboard QTI writers (WP-Q2)
- Patch 6: bbq reader + writer warning (WP-R1)
- Patch 7: blackboard_export_zip reader (WP-R2)
- Patch 8: blackboard_export_zip image write (WP-B1)
- Patch 9: text/html engines (WP-X1)
- Patch 10: integration/roundtrip tests (WP-T2)
- Patch 11: probe kits + probes doc (WP-P1)
- Patch 12: Ultra decision (WP-U1)
- Patch 13: documentation close-out (WP-D1)

## Open questions and decisions needed

Settled decisions:

- BBQ text upload is text-only; BBQ is an image-bearing authoring INPUT to convert from, and its output keeps `<img>` verbatim + warns.
- Maximum portability is the default via the four-value `media_policy`; every engine routes each image through one of the four outcomes.
- File-reference-first: items keep the author's plain `<img src="images/foo.jpg" alt="...">`; there is no `asset:` scheme in item content. The bank owns the base dir + media-resolution policy; the shared media layer scans HTML-bearing fields at read/collect/export time, resolves local files against the base dir, and writers rewrite the src to their platform path in OUTPUT only. Warn on `data:`/absolute/external srcs.
- Resolved (discovery/derivation): (1) asset discovery happens at read/collect/export, never at item construction; (2) per-item references stay derived by scan, not stored; (3) hashes are internal helpers for optional dedup/collision/verification, not identity; (4) imported-ZIP readers extract payloads to a directory and point `media_base_dir` at it (rewriting HTML to relative paths under it), so later writers repackage through the identical derived resolver.
- Resolved (final pre-dispatch questions): (a) the resolver is purely derived except for imported-ZIP/added-bytes payloads, whose only retention is the extraction dir `media_base_dir` points at; (b) the no-image regression is behavior-identical (file set, parsed XML structure, item content, import-relevant paths), not byte-identical, since ZIP metadata/order makes raw bytes brittle; (c) an automated fixture unzips each generated package and asserts its structure/manifest against the matching `SAMPLES/` reference before any manual import; (d) external-URL, data-URI, and SVG warnings are emitted from the single `apply_media_policy` channel so every engine surfaces them consistently.
- PNG/JPEG/GIF first-class; SVG warn-listed; `.webp`/unsupported raise.
- Blackboard Original write is in scope now (evidenced by `SAMPLES/`); ships on sample + in-code roundtrip + automated structure evidence, with sandbox import as optional gate-B verification.
- Rasterization (JS-canvas / hard HTML tables -> PNG) is a separate follow-up tool, not part of this plan.

Evidence captured (`SAMPLES/`, resolves most format unknowns):

- BB `.dat`: two-mechanism wiring confirmed (`SAMPLES/blackboard_learn_classic-bb_export`).
- BB QTI 2.1: root `image-N.jpg` + webcontent + dependency + `<img src="../...">` (`SAMPLES/blackboard_learn_classic-qti21_export`).
- Ultra: `READ_ONLY/question/_<digits>_1/embedded/` + `<a href>` + dependency (`SAMPLES/blackboard_ultra-qti21_export`).

Remaining investigations (gate-owned, do not block M0/M1 core):

- Gate A (Canvas src token): capture a real Canvas image export; decide relative vs `$IMS-CC-FILEBASE$`. Fallback: spec-relative + manual-import check.
- Gate D (Ultra synthesized-id import): confirm a package with our own `_<digits>_1` id imports; else Ultra stays placeholder_warn.

Resolved (exam_yaml, from code evidence):

- exam_yaml is `reference_warn`. `write_item.py:23,29` emits `question_text` verbatim into the YAML `statement` field, so `<img>` HTML carries through unchanged; verbatim reference + itemized warning; write-only, no round-trip claim. Also fix its missing row in `docs/ENGINES.md` (WS-DOCS).
