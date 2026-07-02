# TODO

Backlog items with concrete, actionable next steps. Grouped by topic.

## Fixups
- Engine selection: exact match first, then unique prefix, else error listing candidates.
- ItemBank.merge: preserve first_item_type when allow_mixed is False.
- Detect CRC collisions that overwrite items and warn with item details.
- BBQ NUM writer: avoid divide-by-zero when answer_float == 0.
- Avoid mutating ItemBank order in BaseEngine.process_random_item_from_item_bank.
- Avoid mutating choices_list in BBQ writer when shuffle is enabled.
- Normalize text cleanup (strip &nbsp;, collapse whitespace, remove extra CRC prefixes) in one helper.
- Delete the dead `question_header_classic` and `choice_header_classic` in
  `qti_package_maker/common/franken_bptools.py`: they call nonexistent
  AntiCheat methods and have zero callers.
- Review the root `.gitignore` blanket `*.xml` rule; it forces per-fixture
  `!*.xml` un-ignores (for example under `tests/fixtures/bb_export_slice/`).

## Media sandbox verification
- Import the Canvas gate A probe kit (relative `<img src>` and
  `$IMS-CC-FILEBASE$` variants) into a Canvas Classic Quizzes sandbox and
  record results in [docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md).
- Import the Blackboard Ultra gate D probe kit (a-href and plain `<img>`
  variants, synthesized `_90000001_1` id) and decide whether Ultra should
  package images instead of emitting placeholder text.
- Optional: import the Blackboard Original gate B csfiles probe kit to confirm
  the write-side image path renders on real import.

## Extraction checks
- BBQ reader: validate required field counts per type and include line numbers in errors.
- text2qti reader: stricter block detection and clearer error messages for missing answers.
- Enforce placeholder presence for MULTI_FIB in all readers.
- Validate that MATCH prompts <= choices for readers that accept both lists.

## Reliability tasks
- Add a quiet flag that suppresses prints across interface and engines.
- Add optional deterministic shuffle (seed) for writers that shuffle.
- Centralize warnings to a helper for consistent formatting and testability.
- Ensure HTML validation does not crash on missing lxml; fail with a clear message.

## Tests
- Engine selection: exact match, unique prefix, and ambiguous prefix error case.
- ItemBank.merge: first_item_type preserved and mixed-type rejection enforced.
- BBQ NUM: answer_float == 0 tolerance message does not raise.
- BaseEngine random processing does not reorder the original ItemBank.
- CRC collision warning: verify collisions are reported with details.
- Reader validation coverage for each format (BBQ and text2qti).

## Docs follow-ups
- Update [docs/archive/CODE_DESIGN.md](archive/CODE_DESIGN.md) with engine registry and CRC semantics.
- Document text2qti feedback syntax and planned hint syntax in [docs/FORMATS.md](FORMATS.md).
- Update [docs/ENGINES.md](ENGINES.md) capability tables for readers/writers.
- Add a short note on output determinism to [docs/DEVELOPMENT.md](DEVELOPMENT.md).

## Known limitations
- `blackboard_export_zip` image roundtrip is basename-level (LOM identifier
  basename recovery), a documented fidelity limit rather than a bug.
- HOTSPOT images in `blackboard_export_zip` are read-only; there is no HOTSPOT
  item type to author on write.

## Won't implement
- `canvas_qti_v1_2/write_item.py`: `ORDER` (Canvas does not support it).

## Legacy backlog (retained)
Content migrated from a legacy TODO list. Keep for historical context and to avoid losing items.

## Planned
- Track a histogram of answer choices.
- Clean up `choice_text`, `answer_text`, and `question_text`: remove leading/trailing `&nbsp;`,
  remove extra CRC16 sums at the start of `question_text`.
- Add a quiet mode (less verbose output).
- Add a shuffle mechanism.
- Add general read engine capabilities.
- Hints across formats: see [ROADMAP.md](ROADMAP.md).
- Update README wording where needed.
- Track CRC codes for uniqueness.

## Done
- Image/media support across all engines: shared `media_assets` API, four-value
  `media_policy`, map-based ZIP writer, and image packaging for Canvas QTI 1.2,
  Blackboard QTI 2.1, and Blackboard Original (csfiles). Text and HTML engines
  inline, copy, or placeholder images per policy.
- Full write capability for `human_readable`.
- Full write capability for `bbq_text_upload`.
- BBQ reader supports ORDER, NUM, FIB, and MULTI_FIB.
- `html_selftest` theming to respect MkDocs Material palettes (default/slate)
  using tokens like `--md-default-bg-color`, `--md-default-fg-color`,
  `--md-primary-fg-color`, and `--md-accent-fg-color`, with a
  `prefers-color-scheme` fallback.

## Unimplemented item functions

## Question function signatures
```python
# Question function Types

def MC(item_number: int, crc16_text: str, question_text: str, choices_list: list, answer_text: str):
	...

def MA(item_number: int, crc16_text: str, question_text: str, choices_list: list, answer_list: list):
	...

def MATCH(item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	...

def NUM(
	item_number: int,
	crc16_text: str,
	question_text: str,
	answer_float: float,
	tolerance_float: float,
	tolerance_message=True,
):
	...

def FIB(item_number: int, crc16_text: str, question_text: str, answers_list: list):
	...

def MULTI_FIB(item_number: int, crc16_text: str, question_text: str, answer_map: dict):
	...

def ORDER(item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	...
```

## TODO: implement automatic file type detection (MasterQTIPackage)

### Overview
Enhance `MasterQTIPackage` to automatically detect input file types based on
file extension and contents. This will allow users to call `read()` without
manually specifying the format.

### Steps
1. Detect file type
   - Use file extensions (`.zip`, `.txt`, `.xml`) as an initial hint.
   - Inspect ZIP contents for `imsmanifest.xml` to distinguish between QTI 1.2 and
     QTI 2.1.
   - Check the first line of `.txt` files for BBQ text format.
   - Scan the first 200 characters of `.xml` files for `<questestinterop>` (QTI 1.2) or
     `<assessmentTest>` (QTI 2.1).
2. Read using the correct reader
   - Automatically select the appropriate reader class (`QTIv1Reader`, `QTIv2Reader`,
     `BBQTextReader`, etc.).
   - Store all parsed questions for later conversion.
3. Support multiple reads in one session
   - Allow reading multiple files (`qti12.zip`, `bbq-questions.txt`, etc.).
   - Prevent duplicate reads of the same file.
4. Ensure compatibility with writers
   - Ensure the selected writer can handle all loaded question types.
   - Consider auto-detecting the best writer format based on input.

### Example usage (after implementation)
```python
qpm = MasterQTIPackage(writer="human")
qpm.read("qti12.zip")
qpm.read("qti21.zip")
qpm.read("bbq-questions.txt")
qpm.save("human.txt")
```
