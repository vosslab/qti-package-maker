# Code architecture

## Overview
qti_package_maker moves assessment questions between learning management systems
(LMS platforms such as Canvas, Blackboard, and Moodle). A reader parses questions
out of one format into a shared, format-neutral container; one or more writers then
emit that container in whatever formats you need. Nothing is converted format-to-format
directly, so adding a new format never touches the existing ones.

The shape of the whole system is one hub with plug-in edges:

```text
   readers (in)            item bank (hub)             writers (out)
  +--------------+                                   +----------------+
  | BBQ text     |                                   | Canvas QTI zip |
  | Blackboard   |   parse    +---------------+  emit | Blackboard zip |
  | export zip   | ---------> |   ItemBank    | ----> | Ultra QTI zip  |
  | text2qti     |            |  (CRC-keyed   |       | text / HTML    |
  | okla bqgen   |            |   questions   |       | YAML / Aiken   |
  | ...          |            |   + media)    |       | ...            |
  +--------------+            +---------------+       +----------------+
                                     |
                         shared layers used by both sides
                    media assets  |  zip writer  |  QTI manifest
```

Two terms recur throughout. QTI (Question and Test Interoperability) is the IMS
standard XML packaging that most LMS platforms import. BBQ (Blackboard Question
Upload) is the plain-text question format this tool grew up reading.

## Major components

### Public entry points
- [package_interface.py](../qti_package_maker/package_interface.py) exposes
  `QTIPackageInterface`, the orchestration API: it owns one item bank, looks up
  engines by name, reads packages in, and saves packages out.
- [tools/bbq_converter.py](../tools/bbq_converter.py) is the primary command-line
  front end that wraps `QTIPackageInterface` for terminal use.

### The item bank (the hub)
- [assessment_items/item_bank.py](../qti_package_maker/assessment_items/item_bank.py)
  defines `ItemBank`, the central container. Questions are stored keyed by a CRC16
  (a short checksum of the question used as its identity), which also deduplicates
  items automatically when banks are merged with `+`, `|`, or `merge()`.
- [assessment_items/item_types.py](../qti_package_maker/assessment_items/item_types.py)
  defines the question classes (multiple choice, multiple answer, matching, numeric,
  fill-in-blank, ordering, and so on); each carries its own HTML-bearing fields.
- [assessment_items/validator.py](../qti_package_maker/assessment_items/validator.py)
  checks item content, including tolerant parsing of real-world question HTML.

### Engines (the plug-in edges)
- [engines/base_engine.py](../qti_package_maker/engines/base_engine.py) defines
  `BaseEngine`, the shared contract. Its `process_item_bank()` is the single render
  loop every writer uses, with two optional hooks (a pre-render item transform and a
  post-render output transform) so an engine adds media handling without rewriting
  the loop. Each engine also declares one `media_policy` (see below).
- [engines/engine_registration.py](../qti_package_maker/engines/engine_registration.py)
  discovers engines dynamically: it scans the `engines/` folder, imports each
  `engine_class.py`, and records whether that engine can read, can write, and which
  media policy it uses. Engine folders that start with `template` are skipped.
- Each engine lives in its own folder (for example
  [engines/canvas_qti_v1_2](../qti_package_maker/engines/canvas_qti_v1_2)) with an
  `engine_class.py` plus per-format `write_item.py` and, for readers, `read_package.py`.
  For the full engine list, format details, and how to author one, see
  [ENGINES.md](ENGINES.md) and [ENGINE_AUTHORING.md](ENGINE_AUTHORING.md).

### Shared layers (used by readers and writers alike)
- [common/media_assets.py](../qti_package_maker/common/media_assets.py) is the single
  image layer. It is file-reference-first: question content keeps the author's plain
  `<img src="images/foo.jpg">`, with no special scheme. This module scans HTML for
  image references, classifies each as local / external / data URI, assigns
  collision-safe output names, rewrites `src` values in writer output only, and routes
  every image through one of four media policies. The four policies are `package`
  (bundle the file), `reference_warn` (keep the reference, warn), `placeholder_warn`
  (swap in `[image: name.ext]` text, warn), and `fail` (reject any image). Routing
  every engine through this one module means external-URL, data-URI, and SVG cautions
  read identically everywhere.
- [common/zip_writer.py](../qti_package_maker/common/zip_writer.py) is the shared ZIP
  builder for the four packaging engines. Engines describe an archive as a map of
  archive path to either raw bytes or a source file on disk; entries are written in
  sorted order so archives are deterministic.
- [common/qti_manifest.py](../qti_package_maker/common/qti_manifest.py) builds the
  `imsmanifest.xml` that QTI packages require, including the webcontent resource
  entries that declare bundled images.
- [common/string_functions.py](../qti_package_maker/common/string_functions.py),
  [common/anti_cheat.py](../qti_package_maker/common/anti_cheat.py),
  [common/yaml_tools.py](../qti_package_maker/common/yaml_tools.py), and the
  [common/color_theory](../qti_package_maker/common/color_theory) package hold the
  remaining shared helpers.

## Data flow
A typical read-then-write run moves through the hub once:

- The caller (CLI or `QTIPackageInterface`) picks a reader engine by name and calls
  `read_package(input_file, engine_name)`.
- The reader parses the input into a new `ItemBank`, which is merged into the caller's
  bank; duplicate CRC16 items are dropped on merge.
- For a package that carries images (for example a Blackboard export ZIP), the reader
  extracts image bytes and points the bank's `media_base_dir` at them, or registers
  in-memory bytes through `ItemBank.add_image()`.
- On save, `QTIPackageInterface.save_package(engine_name)` renumbers items and hands
  the bank to the chosen writer engine.
- Just before rendering, a packaging writer calls `ItemBank.collect_assets()`, which
  scans every item's HTML, resolves each image reference once, and assigns output
  names across the whole set. The writer rewrites each item's `<img src>` to its
  packaged path (on a deep copy, never the stored item), bundles the image bytes and
  manifest through the shared ZIP and manifest layers, and applies its media policy.
- The engine writes its output artifact (a ZIP, HTML, text, or YAML file) and returns
  the path. A bank that created its own temporary media directory frees it through
  `ItemBank.cleanup()`.

## Testing and verification
- Full suite: `source source_me.sh && pytest tests/`.
- All-engines smoke run: `source source_me.sh && python3 tests/test_all_engines.py`.
- Repo-wide lint gates run as pytest:
  [tests/test_pyflakes_code_lint.py](../tests/test_pyflakes_code_lint.py),
  [tests/test_ascii_compliance.py](../tests/test_ascii_compliance.py),
  [tests/test_function_typing.py](../tests/test_function_typing.py).
- Media coverage spans unit tests (for example
  [tests/unit/test_media_assets.py](../tests/unit/test_media_assets.py)) and
  integration round trips (for example
  [tests/integration/test_media_end_to_end.py](../tests/integration/test_media_end_to_end.py)),
  backed by the committed real-shape fixture
  [tests/fixtures/bb_export_slice.zip](../tests/fixtures/bb_export_slice.zip), a
  single 12K ZIP with `imsmanifest.xml` at its root; consumers read the ZIP
  directly, since `package_integrity.check_package` accepts ZIP paths.
- Slow end-to-end scripts live under `tests/e2e/` and `tests/playwright/`; see
  [E2E_TESTS.md](E2E_TESTS.md).

## Extension points
- Add a new format by adding an engine folder under
  [engines](../qti_package_maker/engines) with an `engine_class.py`; registration is
  automatic. Copy [engines/template_class](../qti_package_maker/engines/template_class)
  as a starting point and follow [ENGINE_AUTHORING.md](ENGINE_AUTHORING.md).
- Add or adjust question types in
  [item_types.py](../qti_package_maker/assessment_items/item_types.py) and their rules
  in [validator.py](../qti_package_maker/assessment_items/validator.py).
- Extend cross-engine behavior in [common](../qti_package_maker/common) so every engine
  shares one implementation; the media, ZIP, and manifest layers are the pattern to
  follow.
- Add new command-line tools under [tools](../tools).

## Known gaps
- Confirm the final Blackboard Ultra media behavior; the Ultra image path is gated on a
  human decision (see [ROADMAP.md](ROADMAP.md) and
  [docs/active_plans/active/image_support_plan.md](active_plans/active/image_support_plan.md)).
- The empirical results of the LMS image-import probe kits
  ([devel/build_canvas_media_probe.py](../devel/build_canvas_media_probe.py) and
  siblings) are tracked in [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md); confirm which
  `<img src>` token variants each LMS accepts before relying on them.
