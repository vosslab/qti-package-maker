# Formats and engines

## Input formats
- BBQ text upload (`.txt`): tab-delimited rows with one question per line.
- Read support varies by engine. Use the capabilities table in [README.md](../README.md)
  or run `python3 -m qti_package_maker.engines.engine_registration` to inspect availability.
- Mixed question types in a single file require `allow_mixed=True` in the API or
  `--allow-mixed` in `tools/bbq_converter.py`.

## Output formats
- `canvas_qti_v1_2`: QTI v1.2 ZIP for Canvas/ADAPT.
- `blackboard_qti_v2_1`: QTI v2.1 ZIP for Blackboard.
- `bb_ultra_qti_v2_1`: QTI v2.1 ZIP for Blackboard Ultra; write only; strict HTML sanitization.
- `blackboard_export_zip`: Blackboard pool export ZIP; read + write; carries Matching into Ultra.
- `bbq_text_upload`: Blackboard text upload `.txt`.
- `human_readable`: plain-text review format.
- `html_selftest`: self-contained `.html` quiz.
- `text2qti`: plain-text format used by the `text2qti` engine for
  reading/writing.

## Question types
Supported item types are MC, MA, MATCH, NUM, FIB, MULTI_FIB, and ORDER.
See [README.md](../README.md) for the engine-by-engine capability matrix.
