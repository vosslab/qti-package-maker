# Formats and engines

## Input formats
- BBQ text upload (`.txt`): tab-delimited rows with one question per line.
- Read support varies by engine. Use the capabilities table in [ENGINES.md](ENGINES.md)
  or run `python3 -m qti_package_maker.engines.engine_registration` to inspect availability.
- Mixed question types in a single file require `allow_mixed=True` in the API or
  `--allow-mixed` in `tools/bbq_converter.py`.

## Output formats
- `canvas_qti_v1_2`: QTI v1.2 ZIP for Canvas/ADAPT.
- `blackboard_qti_v2_1`: QTI v2.1 ZIP for Blackboard Learn; also imports cleanly into
  Blackboard Ultra via "Import from QTI 2.1 package" (matching questions skipped by Ultra).
- `blackboard_export_zip`: Blackboard pool export ZIP; read + write; also imports into
  Ultra via "Import from file", and carries Matching there.
- `bbq_text_upload`: Blackboard text upload `.txt`.
- `exam_yaml`: YAML-based print-oriented exam format `.yaml`; write only.
- `human_readable`: plain-text review format.
- `html_selftest`: self-contained `.html` quiz.
- `moodle_aiken`: Moodle Aiken plain-text multiple-choice `.txt` (MC only).
- `okla_chrst_bqgen`: plain-text bank-generator `.txt`; read + write.
- `text2qti`: plain-text format used by the `text2qti` engine for
  reading/writing.

## Image and media support

Image support varies by engine. Packaging engines bundle image bytes,
reference engines keep a working `<img>` reference plus a per-image warning,
and placeholder engines substitute `[image: name.ext]` text. See the
per-engine media-behavior table in [ENGINES.md](ENGINES.md).

## Question types
Supported item types are MC, MA, MATCH, NUM, FIB, MULTI_FIB, and ORDER.
See [ENGINES.md](ENGINES.md) for the engine-by-engine capability matrix.
