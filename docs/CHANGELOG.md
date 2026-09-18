# Changelog

## 2026-09-18

### Additions and New Features

- Added opt-in `html_to_image` conversion for Blackboard Ultra-stripped
  table-cell drawings (Playwright screenshot) and RDKit JavaScript canvases
  (RDKit Python API). `blackboard_export_zip` and `blackboard_qti_v2_1` accept
  the keyword (default off). `QTIPackageInterface.save_package()` passes
  `engine_options`, and `tools/bbq_converter.py --html-to-image` forwards it.
  Fixture provenance: DNA gels (`who_father_html.py`, `who_killer_html.py` /
  `gellib.py`), agglutination (`blood_type_agglutination_test.py`), restriction
  maps (`linear_digest.py`), Fischer `padding: 0` cells (`sugarlib.py`), and
  two `moleculelib.py` canvases (legend on/off). Negatives: a plain data table
  and `metaboliclib.py` `padding: 0 2px` labels.

### Behavior or Interface Changes

- Packaged item HTML is unchanged unless `html_to_image` is on. Version is
  26.09. `playwright` and `rdkit` are required runtime dependencies;
  [docs/INSTALL.md](INSTALL.md) documents `playwright install chromium`.

### Fixes and Maintenance

- Removed the unused npm Playwright/TypeScript toolchain
  (`package.json`, `package-lock.json`, `devel/setup_playwright.sh`,
  `devel/setup_typescript.sh`). Table screenshots use pip `playwright`
  and `playwright install chromium`.
- Scoped `--html-to-image` to the two Blackboard packaging engines so mixed
  CLI runs no longer TypeError on Canvas or text writers. Dropped the removed
  `-u` Ultra shortcut from [docs/USAGE.md](USAGE.md), pointed troubleshooting
  at Chromium install, and trimmed Ultra notes that still described the
  converter as unbuilt.
- Refreshed [README.md](../README.md) for the current landing-page contract:
  Ultra table-drawing conversion, the `--html-to-image` Blackboard path, and
  the canonical [LICENSE.LGPL-3.0](../LICENSE.LGPL-3.0) name.
- Pointed [README.md](../README.md) and `pyproject.toml` at the real
  [LICENSE.LGPL-3.0](../LICENSE.LGPL-3.0) file. Loaded `tools/bbq_converter.py`
  and the probe builders in tests via `importlib` instead of importing
  `tools` or `devel` as packages. Recorded `tools/bbq_converter.py` as the
  one support-dir exclusion: it is the setuptools-installed educator CLI.
- Synchronized shared style guides, tests, and repository support files from the starter template.

### Developer Tests and Notes

- Permanent html-to-image tests cover the product contracts only: which
  fragments convert, SMILES-to-PNG, derived-bank replacement without mutating
  the source, MC answer identity after conversion, no media dir on render
  error, and switch-on/switch-off packaging for both engines. The CLI path is
  `tests/e2e/e2e_html_to_image.py`. Fixture-inventory parametrization, a 100px
  screenshot oracle, and optional sibling-repo BBQ scans were removed.
- The four critical generators are table-cell drawings; RDKit canvas conversion
  is implemented but is not required to ship those items.

## 2026-08-25

### Fixes and Maintenance

- Isolated HTML self-test controls by item CRC, made MULTI_FIB answer attributes safe for quotes,
  restored the MA empty-selection message, rejected Boolean and non-finite numeric answers, and
  made direct empty-bank saves fail before creating an output file. Added focused regressions for
  each failure without changing result strings, image handling, or inherited host-page fonts.
  The shared HTML wrapper now also removes trailing spaces and tabs from every emitted line. Audit
  follow-up removed an unreachable empty-bank branch, documented the NUM validation contract, and
  pruned two implementation-text-coupled tests.

### Developer Tests and Notes

- Targeted HTML output, media, validation, pyflakes, typing, and repository whitespace gates: 752
  passed. Full repository suite: 3072 passed.

## 2026-08-20

### Fixes and Maintenance

- Split the Blackboard export ZIP reader into package orchestration, media recovery, and item XML
  parsing modules without changing its public `read_items_from_file()` interface. Moved the HTML
  void-element repair test to the item-parsing module where that behavior now lives.
- Added manager-approved source-file-limit overrides for `floating-wiggling-castle.md` and
  `rust-port-plan.md`; the Blackboard reader is now below the repository line limit.

## 2026-07-14

### Behavior or Interface Changes

- Added `--verbose` to `devel/submit_to_pypi.py`; it passes Twine's detailed upload diagnostics
  through only when requested, while normal successful uploads stay concise. A failed non-verbose
  upload now tells the user to rerun the script with `--verbose`.
- Refreshed `README.md` as a newcomer-focused landing page: added a compact destination and image
  compatibility chart, moved the existing self-test screenshots into a named proof section, added a
  reproducible input-to-three-outputs quick start and Python API example, surfaced Canvas live-import
  limitations before onboarding, aligned package metadata and docs on Python 3.10+ runtime syntax,
  Python 3.11+ `tomllib` development tooling, and the tested Python 3.12 environment, cropped both
  managed self-test screenshots to exact 16:10 frames with accessible before-and-after prose, and
  curated the documentation and support routes. Moved the 2026-07-02 and 2026-07-01 lead summaries
  into their `Developer Tests and Notes` subsections so every day-block entry is categorized.
- Exposed the existing `tools/bbq_converter.py` as a setuptools `script-file`, so PyPI installs the
  educator-facing `bbq_converter.py` command without moving or duplicating its implementation. Kept
  the destructive XML formatter and repository shell helper development-only, and rewrote the
  primary README and usage quick starts around the `pip install` workflow.

## 2026-07-02

### Additions and New Features

- Added `qti_package_maker/common/package_integrity.py`, a shared
  cross-reference integrity check that takes a finished package (ZIP path or
  extracted tree) and returns human-readable violation strings (empty means
  clean). It dispatches on package shape (manifest namespace, resource types,
  `.dat` files), so it works on any flavor including real `SAMPLES/` exports.
  Checks: IMS content-packaging manifest resolution (`<resource href>`,
  `<file href>`, `<dependency identifierref>`); item answer linkage
  (QTI 2.1 `correctResponse` values and QTI 1.2 scored `<varequal>` values
  into choice responses must match a declared interaction choice identifier in
  the same item, a self-consistency check independent of padding scheme);
  rewritten `<img src>` resolution relative to each item file; and
  `blackboard_export_zip` cross-refs (`bbcswebdav/xid-<n>` token to csfiles
  binary and res00005 resourceId, CSResourceLinks `parentId` to a pool
  `bbmd_asi_object_id`, and each csfiles binary to its LOM sidecar).
- Added `tests/integration/test_package_cross_references.py` (10 tests): every
  packaging engine (`canvas_qti_v1_2` relative and file-base variants,
  `blackboard_qti_v2_1`, `bb_ultra_qti_v2_1`, `blackboard_export_zip`) builds a
  representative MC+MA+MATCH+NUM+FIB bank with one embedded image, saves into
  `tmp_path`, and must pass the integrity check with no violations; the
  committed `tests/fixtures/bb_export_slice` ground truth must also pass. Four
  regression canaries prove the check DETECTS the bug class, reproducing the
  two live Blackboard import failures in-test (a QTI 2.1 `correctResponse`
  `answer_002` with `answer_1..N` choices, and a CSResourceLinks `parentId`
  naming an ASI object id no pool item emitted) plus a QTI 1.2 `varequal`
  mismatch and a dangling manifest/media reference. Runs in about 0.2s.
- Created `docs/NEWS.md` and `docs/RELEASE_HISTORY.md` (news-release-docs
  skill), each a single `v26.06 - 2026-07-02` block; `NEWS.md` leads with the
  per-engine image support highlight.
- Prepended `v26.07 - 2026-07-02` blocks to `docs/NEWS.md` and
  `docs/RELEASE_HISTORY.md` (news-release-docs skill) for the GitHub 26.7
  release: package integrity checker, field-verified Blackboard image
  imports (gates D and B PASS), the two live Blackboard import bug fixes,
  and the `bb_ultra_qti_v2_1` engine removal. `NEWS.md` carries the
  `-u`/`--ultra` removal as an upgrade note.
- Added `devel/check_package_integrity.py`, an ad-hoc CLI wrapper around
  `package_integrity.check_package()` for checking any package ZIP or
  extracted directory (real LMS exports, probe kits, suspect ZIPs) outside
  the pytest suite; prints violations one per line plus a `CLEAN`/`N
  violation(s)` summary and raises on a nonzero count.
- Created `docs/COOKBOOK.md` with verified Python-interface recipes:
  Blackboard pool-export conversion (including the `allow_mixed=True` gotcha),
  engine-capability selection (including the `text2qti` `NotImplementedError`
  on MATCH, MULTI_FIB, and ORDER), `html_selftest` into mkdocs-material, and
  image `media_policy` handling.
- Added README screenshots `docs/screenshots/html_selftest_quiz.png` (multiple
  choice with an inline embedded base64 bar-chart figure demonstrating the new
  image-support feature, plus multiple answer and numeric entry) and
  `docs/screenshots/html_selftest_graded.png` (the same multiple choice item
  self-graded CORRECT), rendered via Playwright/Chromium and embedded in the
  managed screenshot block.
- Added `tests/integration/test_cross_format_image_roundtrip.py` (3 tests):
  BBQ -> `blackboard_export_zip` -> read (basename-level byte match),
  BBQ -> `text2qti` -> read (`collect_assets` byte match), and the
  three-format chain BBQ -> `bb_export` -> `text2qti` with bytes identical to
  the original constant. No production changes; no bugs found.
- Extended `docs/MEDIA_LMS_PROBES.md` gate D with a third Ultra import
  variant: converting the existing `bb_export` probe ZIP
  (`output_probes/bb_original/bb_original_probe.zip`) via Ultra's
  course-content conversion importer, to check whether the embedded figure
  survives Original-to-Ultra conversion even where Ultra's native QTI
  importer rejects the QTI 2.1 probes.
- Added `devel/build_sample_control_zips.py`: re-zips the three real
  Blackboard exports under `SAMPLES/` (`blackboard_learn_classic-bb_export`,
  `blackboard_learn_classic-qti21_export`, `blackboard_ultra-qti21_export`)
  into faithful control ZIPs (`control_learn-bbexport.zip`,
  `control_learn-qti21.zip`, `control_ultra-qti21.zip`) so a human can import
  the REAL packages Blackboard itself produced into the same probe sandboxes,
  isolating an LMS image-import ceiling from a writer defect in our own
  generated packages.
- Extended `qti_package_maker/common/package_integrity.py` with two new
  flavor-independent checks that run on every package regardless of manifest
  shape. (1) An image-dimension check: every packaged raster image (`.png`,
  `.jpg`/`.jpeg`, `.gif`) must have `min(width, height) >
  MIN_IMAGE_DIMENSION_PX` (5px); dimensions are read from the file header with
  stdlib only (PNG IHDR, GIF logical screen descriptor, JPEG SOF marker scan)
  via a magic-bytes dispatcher with the entry's extension as a fallback
  cross-check, and an unparsable header is itself a violation. Directly
  prevents a repeat of a real incident: a 1x1-pixel probe image imported into
  Blackboard cleanly but was invisible on the page, costing a full day of
  false "image not imported" verdicts. (2) An identifier-safety check:
  every identifier-bearing attribute the checker already reads (manifest
  `identifier`, `resource identifier`, `dependency identifierref`, QTI 1.2
  `item ident`, QTI 2.1 `assessmentItem identifier`) must be an id-safe token
  matching `^[A-Za-z_][A-Za-z0-9._-]*$`; catches a real bug shipped in our own
  output, a manifest `identifier="main manifest"` containing a literal space.
  Extended `tests/integration/test_package_cross_references.py` with 7 new
  canaries (1x1 PNG/GIF/JPEG dimension, unreadable image header, manifest
  identifier with a space, resource identifier with a space, item ident
  starting with a digit) and replaced the representative test bank's 1x1 PNG
  fixture with an 8x8 visible PNG so the existing parametrized engine-output
  tests keep passing under the new dimension check; full suite still green
  (2906 passed).
- Added a SCORE `outcomeDeclaration` presence check to
  `qti_package_maker/common/package_integrity.py`: flags any QTI 2.1
  `assessmentItem` missing an `outcomeDeclaration identifier="SCORE"`,
  harvested from the removed `bb_ultra_qti_v2_1` engine's compat gate before
  its deletion. Added a canary test in
  `tests/integration/test_package_cross_references.py` proving the check
  detects a missing declaration.

### Behavior or Interface Changes

- Rewrote `README.md` for new-visitor appeal: a 225-character GitHub About
  first paragraph, all seven question types and output targets named, grouped
  doc links, a `bbq_converter` quick start with an explicit placeholder input
  name, the reserved screenshot block, LGPLv3 and Bluesky links, and a new
  "Support and links" section that absorbs `docs/COMMUNITY.md`'s donation and
  social links.
- Rewrote `AGENTS.md` as a bare-path pointer file; refreshed pointers to the
  new doc set (`COOKBOOK`, `FORMATS`, `QUESTION_TYPES`, `TROUBLESHOOTING`,
  `DEVELOPMENT`, `ROADMAP`, `TODO`) and the `ENGINE_AUTHORING` `media_policy`
  contract.
- Rewrote `docs/USAGE.md` and `docs/INSTALL.md`: copy-paste CLI and
  `QTIPackageInterface` quick starts (all examples executed and verified), the
  `source_me.sh` no-install path, an Images section (ZIP `media/` bundling vs
  `html_selftest` data URIs), and probe-kit usage; replaced the stale
  nonexistent `bbq-example-questions.txt` reference.
- Corrected the `pyproject.toml` license classifier from GPLv3 to LGPLv3 to
  match `LICENSE.LGPL_v3` and `README.md` (PyPI metadata; flagged for human
  review).
- `devel/build_ultra_media_probe.py` now emits format-suffixed ZIPs
  (`ultra_probe_ahref-qti21.zip`, `ultra_probe_img-qti21.zip` plus a new
  `ultra_probe_img-bbexport.zip` built through the real `blackboard_export_zip`
  engine) so gate D probes both of Ultra's import systems -- "Import from QTI
  2.1 package" and "Import from file" (the bb_export conversion importer) --
  with the format visible in both the filename and the imported pool title
  ("Ultra Media Probe AHREF QTI21" / "IMG QTI21" / "IMG BBEXPORT").
- Reworked `devel/build_bb_original_probe.py` into a two-variant gate B
  probe kit builder for classic Blackboard Learn, which imports both a
  proprietary `bb_export` package and a QTI 2.1 package via separate menu
  entries: `bb_learn_probe_img-bbexport.zip` (existing `blackboard_export_zip`
  csfiles path, retitled "BB Learn Probe IMG BBEXPORT") and a new
  `bb_learn_probe_img-qti21.zip` (built through the `blackboard_qti_v2_1`
  engine's root-level image write path, titled "BB Learn Probe IMG QTI21").
  Output moved from `output_probes/bb_original/` to `output_probes/bb_learn/`
  for clarity; updated `tests/integration/test_probe_package_structure.py`
  and `docs/MEDIA_LMS_PROBES.md` gate B accordingly.
- Converted the committed real-export fixture `tests/fixtures/bb_export_slice/`
  (18 loose files) into a single `tests/fixtures/bb_export_slice.zip` plus
  `tests/fixtures/bb_export_slice_README.md`; 5 consumer tests now read the
  ZIP directly via `package_integrity.check_package`, which accepts ZIP paths.
  Added a `.gitignore` exception for the fixture ZIP, updated an engine
  comment path reference, and fixed the two doc links that pointed at the
  removed directory tree (`docs/CODE_ARCHITECTURE.md`,
  `docs/FILE_STRUCTURE.md`).

### Fixes and Maintenance

- Fixed the shared `qti_package_maker/common/qti_manifest.py` manifest builder
  (consumed by `canvas_qti_v1_2` and `blackboard_qti_v2_1`) per
  `docs/active_plans/audits/media_import_delta_report.md`'s Pair B findings:
  the root `<manifest identifier="main manifest">` contained a literal space,
  which is not a legal `xs:ID`/`xs:NCName` token and could make an importer
  skip the resource graph; now emits `identifier="man00001"`, matching the
  root identifier used by every real export under `SAMPLES/` (bb_export,
  Learn Classic qti21, Ultra). Also added the missing empty `<organizations/>`
  element before `<resources>`, matching
  `SAMPLES/blackboard_learn_classic-qti21_export/imsmanifest.xml`;
  `bb_ultra_qti_v2_1` and `blackboard_export_zip` already emit both correctly
  via their own separate manifest builders and were unaffected.
- Fixed `blackboard_qti_v2_1/item_xml_helpers.py`'s `assessmentItem` identifier
  minting: `f"{question_crc16}_{rand_crc16}"` could start with a hex digit
  (0-9), which is not a legal `xs:NCName`; now prefixed `f"QUE_{question_crc16}_{rand_crc16}"`,
  matching the `QUE_`-prefixed shape of every real item identifier confirmed
  in `SAMPLES/blackboard_learn_classic-qti21_export/qti21/assessmentItem00001.xml`
  (`QUE__23221280_1`) and the existing `bb_ultra_qti_v2_1` convention.
- Fixed `devel/build_ultra_media_probe.py`'s `build_item_xml` so the probe
  `assessmentItem`'s own `identifier` is `"QUE_" + SYNTHETIC_QUESTION_ID`
  verbatim (`QUE__90000001_1`, double underscore) instead of
  `"QUE" + SYNTHETIC_QUESTION_ID` (`QUE_90000001_1`, single underscore). Per
  `docs/active_plans/audits/media_import_delta_report.md` C2, real Ultra
  exports key the item identifier to `"QUE_"` plus the embedded folder id
  verbatim (folder `_23221289_1` -> identifier `QUE__23221289_1`); the probe's
  single-underscore form did not match its own `_90000001_1` embedded folder,
  so stripping the `QUE_` prefix left `90000001_1` instead of `_90000001_1` --
  a real internal inconsistency the real export never has, and a candidate
  explanation if Ultra keys embedded-file storage off the item identifier.
  `qti_package_maker/engines/bb_ultra_qti_v2_1/item_xml_helpers.py`'s real
  engine identifier minting (`QUE__{crc16_collapsed}_1`) was already correct
  and untouched. Strengthened
  `tests/integration/test_probe_package_structure.py`:
  `test_ultra_probe_kit_matches_samples_layout` now asserts each probe item's
  `@identifier` equals `"QUE_"` plus its embedded folder id, and
  `test_ultra_probe_shape_matches_real_samples_export` now reads each real
  Ultra sample item XML and asserts the same `QUE_` + folder-id
  correspondence, not just manifest-level dependency wiring.
- Audited every identifier our writers mint against
  `qti_package_maker/common/package_integrity.py`'s `IDENTIFIER_SAFE_RE`
  (`^[A-Za-z_][A-Za-z0-9._-]*$`) for XML-ID safety, per a coordinator
  scope-widening request during this task: manifest identifiers (`man00001`,
  `assessment_meta`, `ccresNNNNN`, per-item `base_name` filenames), Ultra/Learn
  `QUE_`-prefixed item identifiers (both fixed above), Ultra's
  `question_bank00001*` test/section/item identifiers, Canvas's
  `multiple_choice_NNN`/`choice_NNN`/`assignment_name` identifiers, and
  `blackboard_export_zip`'s `man00001`/`res0000N`/`_<digits>_1` asi-object-id
  and CSResourceLinks tokens (proprietary Blackboard `.dat` fields, not
  `xs:ID`-typed XML attributes, but already underscore/digit-shaped like the
  real export) all verified clean. Only the two violators fixed above
  (`qti_manifest.py`'s `"main manifest"` and `blackboard_qti_v2_1`'s
  unprefixed crc16 item identifier) were found.
- Fixed the `blackboard_export_zip` engine so embedded csfiles images survive a
  real Blackboard Learn Classic import. The writer minted each `res00005.dat`
  CSResourceLinks `parentId` from the owning item's CRC16 but never emitted a
  matching `<bbmd_asi_object_id>` on the item, so Learn logged "the parent
  associated with the course resource link cannot be located in the package",
  discarded the link record, and dropped the image (question text imported
  fine). `common_xml.build_itemmetadata` now stamps each item's
  `bbmd_asi_object_id` as the first `<itemmetadata>` child, and both that id and
  the CSResourceLinks `parentId` are derived from the one
  `common_xml.make_item_asi_object_id` helper (moved from `assessment_meta`), so
  the parent always resolves inside the package -- exactly as the real export
  matches each `parentId` (e.g. `_23221280_1`) to an item `bbmd_asi_object_id`
  in `SAMPLES/blackboard_learn_classic-bb_export/res00002.dat`. Strengthened the
  structure tests: `tests/integration/test_blackboard_export_zip_output.py` now
  asserts every generated `parentId` resolves to a pool item
  `bbmd_asi_object_id` and pins the same invariant against the committed
  `tests/fixtures/bb_export_slice/` real-export slice, and the two bbexport
  probe cases in `tests/integration/test_probe_package_structure.py` gained the
  same parent-resolution check. A probe rebuild and user re-import of the
  bb_export package are still needed to confirm the image renders in Learn.
- Fixed the `blackboard_qti_v2_1` MC and MA writers so Learn accepts the
  correct answer. `write_item.MC`/`MA` emitted zero-padded correctResponse
  values (`answer_002`) while `item_xml_helpers.create_item_body` emitted
  unpadded simpleChoice identifiers (`answer_2`); Learn could not link the two
  and rejected the item with `mc.no_valid_answer_match` (no correct-answer
  checkmark in the preview). Both writers now emit unpadded `answer_{idx}` ids
  matching the real Learn export (`SAMPLES/blackboard_learn_classic-qti21_export/qti21/assessmentItem00001.xml`
  MC and `assessmentItem00002.xml` MA both use `answer_1`/`answer_2`). MA's
  correctResponse sort is now numeric so double-digit ids order after single
  digits. Added two linkage tests in
  `tests/unit/test_qti_writer_outputs.py` asserting every correctResponse value
  is a declared simpleChoice identifier. MATCH and ORDER already pad both sides
  consistently and were unaffected.
- Fixed the `bb_ultra_qti_v2_1` MA writer's correctResponse sort to match the
  same numeric-id fix applied to `blackboard_qti_v2_1`: `write_item.MA` used a
  plain lexical `answer_id_list.sort()` on unpadded `answer_{idx}` ids, so with
  11+ choices `answer_10` sorted before `answer_2`. Now sorts by the integer
  suffix (`int(answer_id.rsplit("_", 1)[1])`), matching the classic engine's
  idiom. Added `test_ultra_ma_correct_response_order_is_numeric` in
  `tests/integration/test_ultra_engine.py`, an 11-choice MA item with correct
  answers at indexes 2 and 10, asserting the emitted correctResponse values
  land in numeric order matching the declared simpleChoice order.
- Probe builders now route figure bytes through `ItemBank.add_image` with
  `cleanup()`, so `output_probes/` holds only the ZIPs. `devel/build_ultra_media_probe.py`,
  `devel/build_bb_original_probe.py`, and `devel/build_canvas_media_probe.py`
  previously wrote a hand-made persistent media dir (e.g.
  `output_probes/ultra/ultra_probe_bbexport_media/`) beside their output
  ZIPs; each now spills the same JPEG bytes into a bank-owned temp dir via
  `add_image()` and calls `cleanup()` after the ZIP(s) that consume the bank
  are written (once, after both saves, for the Canvas kit's shared bank).
  Leftover `*_media/` dirs under `output_probes/` were removed and all three
  kits rebuilt; `tests/integration/test_probe_package_structure.py` (6 tests)
  still passes, confirming ZIP contents are unchanged.
- Fixed a staging-directory leak on rejected media banks: the file-packaging
  engines (`blackboard_export_zip`, `canvas_qti_v1_2`, `blackboard_qti_v2_1`)
  created their timestamped CWD staging directory BEFORE validating media
  policy, so a data-URI `<img src>` (which raises `MediaPolicyError`) left an
  empty `BB-Export-*` / `QTI12-*` / `QTI21-*` directory behind on every failed
  save. Reordered `save_package` to validate first, create side effects second:
  `blackboard_export_zip` now runs `_plan_image_embedding` (which raises on data
  URIs) before `os.makedirs`, and the two QTI engines call a new shared
  `BaseEngine.raise_on_unpackagable_media` up front, before their `os.makedirs`.
  `bb_ultra_qti_v2_1` uses the placeholder-warn policy and never raises on data
  URIs, so it had no leak. No data-URI raise behavior was weakened.
- Added `tests/integration/test_staging_dir_leak.py`: a parametrized regression
  test that packages a data-URI bank through each raising engine and asserts
  `MediaPolicyError` is raised AND no new staging directory appears in the cwd
  (run hermetically inside `tmp_path` via `monkeypatch.chdir`).
- Fixed `devel/build_ultra_media_probe.py` so the a-href and img-tag gate D
  probe ZIPs carry variant-distinct pool/bank titles ("Ultra Media Probe
  AHREF" / "Ultra Media Probe IMG") instead of both sharing the identical
  humanized package name "ultra media probe"; the user reported the two
  imported Ultra question banks were indistinguishable in the Ultra UI.
  Checked `devel/build_canvas_media_probe.py` for the same defect: its two
  variants already pass distinct `package_name` values ("canvas_probe_relative"
  / "canvas_probe_filebase") straight through as the QTI 1.2 assessment
  title, so no collision exists there.
- Refreshed `docs/CODE_ARCHITECTURE.md` and `docs/FILE_STRUCTURE.md`:
  hub-and-edges overview with an ASCII diagram, the media/zip/manifest shared
  layers, the ItemBank media API, BaseEngine hooks, and the fixture plus
  probe-kit mapping; corrected stale lint-command references.
- Rewrote `docs/RELATED_PROJECTS.md` as a sourced, confidence-tiered ecosystem
  map (bptools, text2qti, and the Oklahoma Christian BlackboardQuizGenerator
  confirmed by in-repo evidence).
- Refreshed `docs/TROUBLESHOOTING.md` with image-support error entries (all
  messages verified in code) and corrected stale install and source-script
  commands.
- Refreshed `docs/DEVELOPMENT.md` (`source_me.sh`, `pip_requirements*.txt`,
  test tiers, typing and pyflakes gates, engine authoring, `devel/` scripts);
  `docs/FAQ.md` was deliberately not created (it would duplicate
  `TROUBLESHOOTING` and `COOKBOOK`).
- Refreshed `docs/ROADMAP.md` and `docs/TODO.md` after the image-support
  close-out (sandbox gates recorded, evidence-grounded follow-ups added,
  completed items removed).
- Expanded `.gitignore`: Python caches, venv, and coverage; a new
  NODE/PLAYWRIGHT section (`node_modules/`, Playwright artifacts); and
  `SAMPLES/` as local-only data.

- Strip leftover `WP-*` planning-tag references from every permanent
  comment and docstring in `qti_package_maker/`, `devel/`, `tests/`, and
  `docs/MEDIA_LMS_PROBES.md` (gate names like "gate A" / "gate D" are kept
  where they name a durable probe, only the internal work-package tag is
  removed). `docs/CHANGELOG.md` and `docs/active_plans/` are left untouched
  as legitimate history and planning documents.
- `docs/BLACKBOARD_ULTRA_NOTES.md` understated shipped behavior: the Images
  section and the sanitizer's `<img>` drop-list note now describe the
  current `placeholder_warn` behavior (a `[image: name.ext]` placeholder is
  substituted into a cloned item before sanitization, with an itemized
  warning) instead of claiming the engine "strips `<img>` unconditionally
  ... and emits nothing." The porting-forecast table row for inline `<img>`
  images is updated to match, and a new "Interim status (pre-gate-D)" note
  states that the placeholder behavior is current and the final verdict on
  real packaged-image rendering lands after the gate-D sandbox probe.
- `docs/FORMATS.md` was missing an `exam_yaml` bullet under "Output
  formats" even though the engine has shipped since the 2026-07-01
  image-support patches; added alongside the other engine bullets.
- `docs/ENGINES.md` "Support-claim status" sentence read as though
  Blackboard Ultra packages images today; reworded to state Canvas Classic
  Quizzes rendering is pending its own sandbox probe (gate A) and
  Blackboard Ultra currently ships placeholder text only, with a
  packaged-image upgrade decided by its own sandbox probe (gate D).
- `docs/FORMATS.md` pointed readers to `README.md` for the engine
  capability matrix, but that table lives in `docs/ENGINES.md`; repointed
  both references to `ENGINES.md` per the same-directory link rule in
  `docs/MARKDOWN_STYLE.md`.
- Deduplicated the per-engine media render loop (style-audit HIGH). Six
  `engine_class.py` files (`moodle_aiken`, `okla_chrst_bqgen`,
  `human_readable`, `text2qti`, `canvas_qti_v1_2`, `blackboard_export_zip`)
  each re-implemented `BaseEngine.process_item_bank` to inject a media step,
  and `bb_ultra_qti_v2_1` ran a parallel prep loop. `process_item_bank` now
  takes two optional hooks, `item_transform_fn` (pre-render) and
  `post_render_fn` (post-render); every engine keeps only its transform
  function and calls the shared loop, so all seven hand-rolled loops are gone
  with byte-identical output (full suite still 2799 passed, plus 2 new hook
  unit tests). `blackboard_qti_v2_1` keeps its per-item file-writing loop
  (genuinely different) but was folded into the closure cleanup. Added
  `media_assets.make_src_map_fn(src_map)` and routed the three triplicated
  src-map closures (`canvas_qti_v1_2`, `blackboard_qti_v2_1`,
  `blackboard_export_zip`) through it, dropping the unnecessary
  late-binding default-arg guard. `docs/ENGINE_AUTHORING.md` now documents
  the render-loop hooks so new engines never copy the loop.
- Corrected `docs/archive/CODE_DESIGN.md`'s stale "License" line from GPL v3
  to LGPL v3, and set `pyproject.toml`'s `license-files` to
  `["LICENSE.LGPL_v3"]` so built distributions bundle the license text, per
  user confirmation that the project (user-held copyright) is LGPLv3.
- Fixed `tests/unit/test_docs_consistency.py::test_docs_engine_names_in_registry`,
  which had started failing after gate-A doc edits added the backticked
  `canvas_src_variant` token (an EngineClass constructor kwarg, not an engine
  name) to `docs/ENGINES.md`. Added a small, explicitly commented
  `DOC_NON_ENGINE_IDENTIFIERS` allowlist to the test instead of weakening its
  engine-name matching, so the test still fails on a misspelled or
  unregistered engine-like name.
- Review follow-ups: added
  `tests/unit/test_qti_writer_outputs.py::test_qti21_ma_correct_response_order_is_numeric`,
  an 11-choice MA case (mirroring
  `tests/integration/test_ultra_engine.py::test_ultra_ma_correct_response_order_is_numeric`)
  that catches lexical-vs-numeric `correctResponse` sort regressions the prior
  4-choice `blackboard_qti_v2_1` MA test could not reach. Also de-duplicated
  `qti_package_maker/engines/blackboard_export_zip`'s
  `CSFILES_SRC_PREFIX = "@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/"`
  constant, previously defined independently (kept in sync only by a
  "must stay byte-identical" comment) in both `assessment_meta.py` and
  `read_package.py`; it now lives once in the already-shared `common_xml.py`
  and both modules (plus
  `tests/integration/test_blackboard_export_zip_output.py`) import it from
  there. No behavior change.
- Replaced the `PROBE_JPEG_BYTES` constant in all three probe kit builders
  (`devel/build_ultra_media_probe.py`, `devel/build_bb_original_probe.py`,
  `devel/build_canvas_media_probe.py`) with a 240x120 bright red JPEG with a
  white border (~3.6 KB), rebuilt from a 1x1-pixel red JPEG (633 bytes). A
  real Blackboard import discovered that the 1x1 probe figure imports and
  renders perfectly -- as an invisible dot -- which had invalidated a full
  day of "image did not appear" interpretations from earlier probe imports;
  this was the day's key false-negative source. The probe figure must be
  unmistakably visible at a glance, so it is now generated at a real
  on-screen size with high-contrast color. `probe-figure.jpg` filenames and
  alt text are unchanged; all three probe kits were rebuilt into
  `output_probes/{ultra,bb_learn,canvas}/`.
- Renamed the root `<manifest identifier>` from `"man00001"` to
  `"main_manifest"` in all four packaging engines' manifest builders
  (`qti_package_maker/common/qti_manifest.py`, shared by `canvas_qti_v1_2` and
  `blackboard_qti_v2_1`; `qti_package_maker/engines/bb_ultra_qti_v2_1/assessment_meta.py`;
  `qti_package_maker/engines/blackboard_export_zip/assessment_meta.py`), per
  maintainer preference for one clear, readable label over Blackboard's
  cryptic incrementing numbers, and for a single consistent identifier now
  that all four engines share it. The identifier is an opaque `xs:ID` value
  with no importer contract; `res0000N.dat` filenames, `xid` tokens, and
  `.dat` structure (the actual importer contracts) are unchanged. Full suite
  (2906 tests) still green.
- Recorded the final human-verified visible-figure import round in
  `docs/MEDIA_LMS_PROBES.md` (new results-table rows for both gate D
  variants plus gate B optional, a `Status: PASS` line on each gate's
  heading, and final-verdict paragraphs correcting the earlier
  false-negative readings) and in `docs/BLACKBOARD_ULTRA_NOTES.md` (a new
  "Gate D PASS" note, the round-trip and porting-forecast table rows
  updated from "does not appear after import" to "renders", and the
  Ultra-native image embedding and deferred-project sections repointed
  from "pending investigation" to "landing in WP-U1"). No code change; see
  "Decisions and Failures" below for the evidence summary.

### Removals and Deprecations

- Removed `test_ultra_probe_shape_matches_real_samples_export` from
  `tests/integration/test_probe_package_structure.py`: it read
  `SAMPLES/blackboard_ultra-qti21_export/imsmanifest.xml` (and the item XML
  it references) at runtime, but `SAMPLES/` is a gitignored temp directory
  (`.gitignore:31`) that no longer exists, so the test could not run. This
  was a `PYTEST_STYLE.md` "Inline inputs, not external data files"
  violation; per the same doc, deleted rather than rewritten. Dropped the
  now-unused `import re`. Reworded the module docstring: the five remaining
  probe tests assert the QTI-spec-derived, engine-produced shape into
  `tmp_path` (and the tracked `tests/fixtures/bb_export_slice.zip`), none
  read `SAMPLES/`. Swept the rest of `tests/` for the same failure mode --
  no other test reads a gitignored/untracked path; remaining external reads
  target `tmp_path` outputs, tracked fixtures, or tracked repo source. File
  still passes (5 tests, ~0.1s), pyflakes clean.
- Removed `docs/COMMUNITY.md` after merging its links into `README.md`
  (`REPO_STYLE.md` lists it under docs not to use).
- Archived completed planning docs via `git mv`:
  `docs/COLOR_WHEEL_REFACTOR_PLAN.md`, `docs/TEST_PLAN.md`, and
  `docs/CODE_DESIGN.md` moved to `docs/archive/`;
  `TEMP_RDKit_QTI_IMPORT_NOTES.md` moved to
  `docs/active_plans/audits/rdkit_qti_import_notes.md`. Removed stale
  commented-out GPL license notes from `pyproject.toml`.
- Removed the `bb_ultra_qti_v2_1` engine as redundant: deleted
  `qti_package_maker/engines/bb_ultra_qti_v2_1/` (8 files: `__init__.py`,
  `assessment_meta.py`, `compat_gate.py`, `engine_class.py`,
  `html_sanitize.py`, `item_xml_helpers.py`, `type_normalize.py`,
  `write_item.py`) and its 4 committed dedicated test files
  (`tests/integration/test_ultra_engine.py`,
  `tests/test_ultra_compat_gate.py`, `tests/test_ultra_html_sanitize.py`,
  `tests/test_ultra_type_normalize.py`) plus 2 never-committed test files
  staged earlier the same day from the image-support work
  (`tests/unit/test_bb_ultra_media.py`,
  `tests/integration/test_bb_ultra_media_policy_modes.py`), plus the `-u`/`--ultra`
  (`--qti21-ultra`) CLI flag from `tools/bbq_converter.py`. Updated
  `docs/ENGINES.md` (dropped the engine's section, registry row, item-type
  column, and media-behavior row; added a "Blackboard Ultra support (no
  dedicated engine)" section naming `blackboard_qti_v2_1` and
  `blackboard_export_zip` as the two paths that now serve Ultra),
  `docs/BLACKBOARD_ULTRA_NOTES.md` (dead links to the deleted engine and
  test source fixed or dropped; every "landing in WP-U1" /
  "engine upgrade in progress" forward-looking statement replaced with the
  removal decision, historical findings kept intact), `docs/FORMATS.md`,
  `docs/FILE_STRUCTURE.md`, `docs/COOKBOOK.md`, and `docs/ENGINE_AUTHORING.md`.

### Decisions and Failures

- Kept the `LICENSE.LGPL_v3` filename deliberately (user confirmed GitHub
  license detection handles it); an audit suggestion to rename it to `LICENSE`
  was applied, then reverted on user correction.
- Gate A's Canvas sandbox probe (`docs/MEDIA_LMS_PROBES.md`) is blocked:
  Instructure discontinued the Free for Teacher program, so no Canvas
  sandbox is available. Activated the plan's documented fallback for an
  inconclusive gate A: `canvas_qti_v1_2` ships the spec-relative `<img src>`
  variant as default, the `$IMS-CC-FILEBASE$` variant stays selectable via
  the `canvas_src_variant` constructor kwarg, and the probe kit
  (`devel/build_canvas_media_probe.py`) is retained for future institutional
  Canvas access.
- Gate D executed on the user's real Blackboard Ultra SaaS sandbox ("Ultra
  Sandbox - NVoss"): all three Ultra import paths (QTI 2.1 `<a href>`, QTI
  2.1 plain `<img>`, and the `bb_export` "Import from file" conversion path)
  imported the probe question cleanly but the embedded image did not appear
  after import on any path. Per the image-support plan, declared the
  `bb_ultra_qti_v2_1` engine's `placeholder_warn` media policy final; no
  upgrade to a `package` policy is possible given Ultra's importer behavior.
  See `docs/MEDIA_LMS_PROBES.md` and `docs/BLACKBOARD_ULTRA_NOTES.md`.
- **Correction (same day):** the "Ultra strips media" conclusion above is
  retracted. The user built and imported control ZIPs
  (`devel/build_sample_control_zips.py`, faithful re-zips of Blackboard's own
  real exports under `SAMPLES/`, no writer code of ours involved) into the
  same sandboxes: `control_ultra-qti21.zip` rendered its image inline in
  Ultra (pool "a blank pool"), and both `control_learn-bbexport.zip` and
  `control_learn-qti21.zip` rendered their images in Blackboard Learn
  Original. All three control packages Blackboard's own exporter produced
  render their images on import, so there is no LMS ceiling on media
  anywhere in this probe matrix -- every documented "media loss" observation
  above was specific to packages our own writers generated. Whether the
  image binary was never loaded into the content store or was loaded but not
  linked from the question HTML is undetermined; a root-cause investigation
  is now open (`docs/active_plans/audits/media_import_delta_report.md`).
  `placeholder_warn` stays the shipped default for `bb_ultra_qti_v2_1` while
  that investigation runs; the upgrade path to a `package` media policy is
  re-opened. Updated `docs/MEDIA_LMS_PROBES.md`, `docs/BLACKBOARD_ULTRA_NOTES.md`,
  `docs/ENGINES.md`, and `docs/active_plans/active/image_support_plan.md`
  accordingly.
- **Final verdict (same day, visible-figure round): gate D = PASS, gate B
  (optional) = PASS.** The root-cause investigation traced every
  "media-not-imported" result above to a false negative: the probe figure
  was a 1x1-pixel test image (the same root cause the new
  `package_integrity.py` dimension check above now guards against), real
  and correctly imported and linked by Blackboard but invisible on the
  page. Combined with the two real writer bugs also fixed the same day (a
  QTI 2.1 `correctResponse` `answer_002` vs `answer_2` padding mismatch,
  and `blackboard_export_zip`'s missing `bbmd_asi_object_id` for
  `CSResourceLinks` `parentId`; see "Fixes and Maintenance" above), the
  probe kits were rebuilt with a visible 240x120 red figure and the user
  re-imported all variants on real Roosevelt University Blackboard
  instances: `ultra_probe_ahref-qti21.zip` and `ultra_probe_img-qti21.zip`
  ("Import from QTI 2.1 package") both render inline in Ultra;
  `ultra_probe_img-bbexport.zip` ("Import from file") also renders in
  Ultra; `bb_learn_probe_img-bbexport.zip` (Pools import) and
  `bb_learn_probe_img-qti21.zip` (QTI 2.1 import) both render with the
  correct answer marked in Learn Classic; and, as a bonus cross-import,
  `ultra_probe_img-bbexport.zip` also renders when imported into Learn
  Classic instead of Ultra. Gate D verdict: both the a-href and plain
  `<img>` QTI 2.1 patterns render in Ultra, and a synthesized `_<digits>_1`
  id imports cleanly. Gate B (optional) verdict: the `bb_export` engine
  output imports and renders in both Learn and Ultra. Gate A (Canvas)
  remains BLOCKED (Free for Teacher discontinued). Updated
  `docs/MEDIA_LMS_PROBES.md` and `docs/BLACKBOARD_ULTRA_NOTES.md`
  accordingly; `docs/ENGINES.md` follows in a separate pass once the
  `bb_ultra_qti_v2_1` `package` media policy upgrade (WP-U1) lands.
- **Decision (same day, follow-up to the WP-U1 plan above): remove the
  `bb_ultra_qti_v2_1` engine instead of upgrading it.** The engine was
  agent-scaffolded 2026-04-14 on the assumption that Blackboard Ultra
  needed its own dedicated QTI 2.1 writer. User field evidence recorded
  2026-07-02 (see "Developer Tests and Notes" below) showed every
  `blackboard_qti_v2_1` export the user has ever tried already imports
  successfully into Ultra, with only per-feature degradation (matching
  questions skipped, table widths removed, color removed, most inline CSS
  removed) rather than package rejection, and the gate D visible-figure
  probe round confirmed images render in Ultra both from
  `blackboard_qti_v2_1`-shaped QTI 2.1 ("Import from QTI 2.1 package") and
  from `blackboard_export_zip` ("Import from file", which also carries
  Matching, the one item type Ultra's QTI 2.1 importer skips). With both
  gaps already covered by existing engines, a dedicated Ultra writer was
  redundant, so the WP-U1 `package` media policy upgrade planned above
  never landed; the engine was deleted instead. See "Removals and
  Deprecations" above for the exact files removed.
- Implemented and then removed, same day, a hidden anti-cheat-span integrity
  check (flagging invisible `font-size:1px`/`color:white` watermark spans,
  harvested from the removed Ultra engine's HTML sanitizer) per user
  decision: anti-cheat watermark handling is outside this repo's purview.

### Developer Tests and Notes

- Completed an audit follow-up on the 2026-07-01 image-support close-out: mechanical
  comment/docstring cleanup, three doc corrections, and a full doc-set refresh for new visitors.
  No production code changed; the full suite still passed 2799 tests.
- Recorded user-verified field evidence in `docs/BLACKBOARD_ULTRA_NOTES.md`:
  every `blackboard_qti_v2_1` export the user has tried imports successfully
  into Ultra, with per-feature degradation (matching questions skipped, table
  widths removed, color removed, most inline CSS removed) rather than package
  rejection. No code change.
