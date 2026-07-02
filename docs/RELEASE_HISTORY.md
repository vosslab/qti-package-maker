# Release history

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
