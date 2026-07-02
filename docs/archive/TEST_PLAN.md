# Pytest test plan

This document captures ideas for a full pytest suite. It is a staging list
before implementing tests.

## Goals
- Cover core item validation and ItemBank behavior.
- Add fast unit tests for utilities and helpers.
- Add light integration tests for engine outputs and CLI behavior.
- Keep tests deterministic and clean up outputs.

## Proposed structure
- `tests/unit/` for pure Python logic.
- `tests/integration/` for engine outputs and subprocess CLI runs.
- `tests/conftest.py` fixtures: `sample_items`, `sample_bbq_lines`, `tmp_cwd`.

## Unit test ideas
- `qti_package_maker/assessment_items/item_types.py`
  - Construct MC, MA, MATCH, NUM, FIB, MULTI_FIB, ORDER with valid inputs.
  - Verify `item_crc16` format, `item_type`, and answer index fields.
  - `BaseItem.copy()` deep copy behavior.
  - `get_tuple()` rejects empty supporting fields.
- `qti_package_maker/assessment_items/validator.py`
  - `validate_string_text` rejects empty and too short strings.
  - `validate_list_of_strings` rejects duplicates and too-short lists.
  - `validate_MULTI_FIB` requires placeholders in question text.
  - `validate_NUM` rejects negative tolerance.
- `qti_package_maker/assessment_items/item_bank.py`
  - `allow_mixed=False` rejects mixed types; `allow_mixed=True` allows them.
  - Duplicate CRCs are skipped with a warning.
  - `merge`, `__add__`, `__or__`, `__eq__` are order-independent.
  - `__getitem__` slice returns a new ItemBank; int returns an item.
  - `__setitem__` reorders without losing keys.
- `qti_package_maker/common/string_functions.py`
  - `strip_crc_prefix`, `strip_prefix_from_string`, `remove_prefix_from_list`.
  - `number_to_letter`, `number_to_lowercase`, `number_to_roman` bounds.
  - `_html_table_to_text` returns table content instead of placeholder.
- `qti_package_maker/common/qti_manifest.py`
  - QTI 1.2 rejects multiple assessment files.
  - QTI 1.2 rejects mismatched dir and base names.
  - Resources list includes dependencies and assessment meta.
- `qti_package_maker/common/yaml_tools.py`
  - `UniqueKeyLoader` rejects duplicate keys.
  - `applyReplacementRulesToText` and list variants respect overrides.
- `qti_package_maker/engines/engine_registration.py`
  - Registry includes known engines from docs.
  - `can_read` and `can_write` reflect implemented methods.
- `tools/bbq_converter.py`
  - `extract_core_name` accepts `bbq-<name>-questions.txt` and rejects others.
- `qti_package_maker/engines/bbq_text_upload/read_package.py`
  - Parse each BBQ question type to the correct item class.
  - Unknown type raises `ValueError`; blank lines return `None`.
  - MULTI_FIB parsing handles multiple variable blocks.

## Integration test ideas
- `qti_package_maker/package_interface.py`
  - `init_engine` accepts partial names and rejects unknown ones.
  - `trim_item_bank` reduces the count without errors.
- Engine outputs using `tmp_path` and `monkeypatch.chdir`:
  - `canvas_qti_v1_2` zip exists with `imsmanifest.xml` and item XML.
  - `blackboard_qti_v2_1` zip exists with manifest and item XML.
  - `human_readable` contains expected question text and tables.
  - `html_selftest` contains expected HTML and item text.
  - `bbq_text_upload` output is tab-delimited with correct flags.
- CLI smoke test for `tools/bbq_converter.py` using `subprocess` and `PYTHONPATH`.

## Nice-to-have regression tests
- `qti_package_maker/common/anti_cheat.py` excludes tags and uses seeded randomness.
- Docs consistency checks for engine names versus registry.
