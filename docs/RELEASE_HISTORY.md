# Release history

## v26.07 - 2026-07-02

### Highlights

- New shared package integrity checker
  `qti_package_maker/common/package_integrity.py`: takes a finished package
  (ZIP path or extracted tree) and returns human-readable violation strings.
  Checks IMS manifest reference resolution, item answer linkage (QTI 2.1
  `correctResponse` and QTI 1.2 scored `varequal` values must name a declared
  choice), rewritten `<img src>` resolution, `blackboard_export_zip`
  cross-references (xid tokens, CSResourceLinks `parentId`, LOM sidecars),
  a minimum image-dimension check (flags invisible tiny rasters), an
  identifier-safety check, and a QTI 2.1 SCORE `outcomeDeclaration` presence
  check. An ad-hoc CLI wrapper lives at `devel/check_package_integrity.py`.
- Blackboard image support is now field-verified end to end. Human imports on
  real Blackboard Ultra and Learn Classic instances confirmed embedded figures
  render on every import path (QTI 2.1 a-href, QTI 2.1 plain img, and the
  bb_export pool path); see [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md). Earlier
  "image did not import" verdicts were traced to a false negative: a 1x1-pixel
  probe figure that imported cleanly but was invisible on the page.
- Probe kits reworked: the probe figure is now a visible 240x120 red JPEG,
  probe ZIPs carry format-suffixed names and variant-distinct pool titles, a
  two-variant Learn kit covers both import menus, and
  `devel/build_sample_control_zips.py` re-zips the real Blackboard exports
  under `SAMPLES/` into control packages for isolating LMS ceilings from
  writer defects.
- New cross-format image roundtrip tests
  (`tests/integration/test_cross_format_image_roundtrip.py`) prove image bytes
  survive BBQ to bb_export to text2qti chains, and
  `tests/integration/test_package_cross_references.py` runs the integrity
  check against every packaging engine's output plus a committed real-export
  fixture, with regression canaries reproducing both live import failures.
- Deduplicated the per-engine media render loop: `process_item_bank` gained
  `item_transform_fn` and `post_render_fn` hooks, removing seven hand-rolled
  engine loops with byte-identical output.
- Full doc-set refresh: rewritten `README.md`, new [COOKBOOK.md](COOKBOOK.md)
  with verified recipes, rewritten [USAGE.md](USAGE.md) and
  [INSTALL.md](INSTALL.md), refreshed architecture and troubleshooting docs,
  and README screenshots of the self-test HTML.

### Notable fixes

- Fixed the `blackboard_qti_v2_1` MC and MA writers so Learn accepts the
  correct answer: `correctResponse` emitted zero-padded ids (`answer_002`)
  while choices were unpadded (`answer_2`), so Learn rejected items with
  `mc.no_valid_answer_match`. Both sides now emit unpadded ids matching real
  Learn exports; MA correctResponse ordering is now numeric.
- Fixed the `blackboard_export_zip` writer so embedded csfiles images survive
  a real Learn import: each item now stamps a `bbmd_asi_object_id` matching
  its CSResourceLinks `parentId`, so Learn can resolve the link record instead
  of discarding the image.
- Fixed the shared QTI manifest builder: the root manifest identifier
  contained a literal space (not a legal `xs:ID`), and the required empty
  `<organizations/>` element was missing.
- Fixed `blackboard_qti_v2_1` item identifier minting to carry the `QUE_`
  prefix so identifiers cannot start with a digit (illegal `xs:NCName`).
- Fixed a staging-directory leak: file-packaging engines now validate media
  policy before creating their timestamped staging directory, so rejected
  data-URI banks no longer leave empty directories behind.
- Probe builders now route figure bytes through `ItemBank.add_image` with
  cleanup, so `output_probes/` holds only ZIPs.

### Compatibility notes

- Removed the `bb_ultra_qti_v2_1` engine and the `-u`/`--ultra` CLI flag from
  `tools/bbq_converter.py`. Field evidence showed `blackboard_qti_v2_1`
  exports already import into Ultra (with per-feature degradation, not
  rejection) and `blackboard_export_zip` covers Matching, so a dedicated
  Ultra writer was redundant. See [ENGINES.md](ENGINES.md).
- The root `<manifest identifier>` is now `main_manifest` in all packaging
  engines (an opaque `xs:ID` with no importer contract).
- The committed real-export fixture moved from a loose directory to
  `tests/fixtures/bb_export_slice.zip`.
- The `pyproject.toml` license classifier was corrected from GPLv3 to LGPLv3,
  matching `LICENSE.LGPL_v3`.
- `docs/COMMUNITY.md` was removed; its links moved into `README.md`.

### Validation

- Full suite green: 2906 tests passed.
- The integrity check passes on every packaging engine's representative
  output and on the committed real Blackboard export slice; 12 regression
  canaries prove it detects the bug classes it guards.
- Human-verified import rounds on real Blackboard Ultra and Learn Classic
  instances: gate D (Ultra) PASS, gate B (Learn, optional) PASS. Gate A
  (Canvas) remains blocked because Instructure discontinued the Free for
  Teacher program; the Canvas probe kit is retained.

## v26.06 - 2026-07-02

### Highlights

- Per-engine image and media support across all engines. A new shared asset
  API in `qti_package_maker/common/media_assets.py` scans question HTML for
  assets, resolves them with loud failures on traversal escape or unsupported
  types, classifies sources (local, external, data-uri), assigns deterministic
  output names, rewrites writer output, and applies one of four media policies.
  PNG, JPEG, and GIF are first-class; SVG is packaged with a warning; other
  extensions raise.
- A four-value `media_policy` (`package`, `reference_warn`, `placeholder_warn`,
  `fail`) routed through a single warning channel, with `reference_warn` as the
  engine default. Every engine now has documented, per-engine media behavior.
- Image handling wired into each engine in the format its target expects: the
  Canvas QTI 1.2 writer packages images under `media/`; the Blackboard QTI 2.1
  writer packages root images; `html_selftest` inlines base64 data URIs;
  `text2qti` writes markdown image references with copied files; `moodle_aiken`
  and `okla_chrst_bqgen` emit `[image: name.ext]` placeholders with citations;
  `exam_yaml` keeps `<img>` verbatim; `bb_ultra_qti_v2_1` uses
  `placeholder_warn`; the `blackboard_export_zip` engine embeds images through
  the native `csfiles/home_dir` path with byte-fidelity roundtrip.
- New read and write engine `qti_package_maker/engines/blackboard_export_zip/`
  for Blackboard's proprietary pool-export package format (the format
  Blackboard's UI calls "Pool"). Supports MC, MA, MATCH, FIB, NUM, and
  MULTI_FIB; auto-registers for read and write; exposed via the `-B`
  (`--bbexport`) CLI flag on `tools/bbq_converter.py`.
- Readers gained media capture: `bbq_text_upload` sets `media_base_dir` to the
  input directory, and `blackboard_export_zip` resolves `csfiles` `@X@` xid
  tokens and hotspot files, extracts them, and rewrites HTML to the
  file-authored shape, all behind a zip-slip extraction guard.
- `ItemBank` plumbing for media: `media_base_dir`, `add_image()` (traversal
  guarded), a derived `collect_assets()`, ownership-gated `cleanup()`, and
  `set_media_base_dir(path, owned=)`. A new map-based ZIP builder in
  `qti_package_maker/common/zip_writer.py` backs the four ZIP engines.
- The engine registry table now shows a Media Policy column.
- Self-test HTML visual refresh: rounded feedback pills that engage on every
  answer check, larger touch-friendly radio and checkbox controls, dark-mode
  input and button theming, disabled-state styling for the Check Answer button,
  and non-color accessibility markers via CSS generated content.

### Notable fixes

- `ItemBank.merge()` dropped `media_base_dir`, so every
  `read_package()` lost it; fixed with carry-forward and a
  different-directories guard.
- The shared `SRC_ATTR_PATTERN` matched `data-src=` and caused a `KeyError` in
  `html_selftest` plus silent substitution skips in several engines; fixed with
  a lookbehind, and the pattern was made public and deduped from six private
  copies.
- Multiple `blackboard_export_zip` scoring and reader corrections to match real
  Blackboard exports: MA `<and>` scoring structure and reader `<not>`-aware
  correct-choice detection, MATCH right-side pool sibling placement (was
  rendering an empty bank on live Ultra import), FIB feedback wiring, and the
  MC/MA `response_lid` literal-ident scoring link.
- Blackboard Ultra "Oops! Something broke." question-expand crash pinned to a
  table-whitespace pattern and fixed by stripping whitespace-only text nodes
  inside table-structure elements.
- `html_selftest` FIB JavaScript fixes (missing f-string prefix, JSON-safe
  answer arrays, theme-var colors) and a mojibake fix widening non-ASCII
  escaping to all codepoints above U+007F.
- Typing-gate campaign brought the repo from 126 failing files to zero typing
  failures, and fixed a nested-def return-inference bug in the sweep tooling.

### Compatibility notes

- The CalVer bump from 26.03 to 26.06 signals that cached `html_selftest`
  self-test fragments are stale and should be regenerated; the engine output
  changed (FIB fixes, non-ASCII escaping, feedback-pill CSS, disabled button
  state, larger controls).
- The `blackboard_export_zip` engine skips ORDER items with a named warning.
- The `blackboard_export_zip` test suite was slimmed to self-contained, fast
  pytests because the sample pool directory is not committed; sample-dependent
  reproduction and scaffolding tests were removed in favor of an in-code
  roundtrip.

### Validation

- Full suite 2799 passed as of the 2026-07-02 audit follow-up (mechanical
  comment cleanup and doc corrections, no behavior change).
- The image-support plan was spec and quality reviewed, remediated, and
  verified. Probe kits for the Canvas and Ultra sandbox gates are staged in
  `output_probes/` with import steps in
  [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md); the Ultra packaged-image decision
  awaits a human sandbox import.
