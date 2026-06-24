# Changelog

## 2026-06-23

### Additions and New Features
- Add new read+write engine `qti_package_maker/engines/blackboard_export_zip/` that emits and parses Blackboard's proprietary pool-export package format (a QTI-1.2-derived `questestinterop` envelope with BB extensions; Blackboard's UI calls it "Pool", never "QTI 1.2"). Engine files: per-type builder modules `MC.py`, `MA.py`, `MATCH.py`, `FIB.py`, `NUM.py`, `MULTI_FIB.py` plus shared primitives in `common_xml.py`; `assessment_meta.py` (bb: namespace manifest + questestinterop/assessment/section wrapper + res00001/res00003-07 sidecars + `.bb-package-info`/`.bb-log-info`); `write_item.py` (MC/MA/MATCH/FIB/NUM/MULTI_FIB dispatch); `engine_class.py` (EngineClass with `save_package` and `read_items_from_file`); `read_package.py` (reader). Engine auto-registers (`can_read` and `can_write`). Supported item types: MC, MA, MATCH, FIB, NUM, MULTI_FIB; ORDER skipped with a named warning; media/images are out of scope. CLI flag `-B`/`--bbexport` added to `tools/bbq_converter.py`. M0 forgeability audit added at `docs/active_plans/audits/blackboard_export_zip_forgeability.md`.

### Fixes and Maintenance
- Rewrite MA correct-answer resprocessing in `qti_package_maker/engines/blackboard_export_zip/MA.py` (`build_MA`) to match the real Blackboard MA scoring structure. The prior bare-varequal shape did not score on Blackboard Ultra because it did not emit the required `<and>` over all choices. The correct branch is now one `<respcondition title="correct">` with `<conditionvar><and>...</and></conditionvar>` listing every choice in original order (correct choices as bare `<varequal respident="response" case="No">IDENT</varequal>`, incorrect choices wrapped in `<not><varequal .../></not>`), followed by `<setvar variablename="SCORE" action="Set">SCORE.max</setvar>` and `<displayfeedback linkrefid="correct" feedbacktype="Response"/>`. Per-choice penalty branches (one per choice) follow the correct branch. A new MA-specific helper `_build_ma_correct_respcondition(label_idents, correct_idents)` implements this; `build_MA` now passes all `label_idents` (not just `correct_idents`) so the `<and>` can list every choice. MC output is unchanged; an MC regression test confirms the single bare `varequal respident="response"` + `setvar SCORE.max` shape.
- Fix MA reader in `qti_package_maker/engines/blackboard_export_zip/read_package.py`: the old `_correct_choice_idents` used `respcondition.iter("varequal")` which descended into `<not>` wrappers, causing incorrect choices to be treated as correct when reading real Blackboard MA XML. Real BB MA encodes one `<respcondition title="correct">` with an `<and>` listing every choice in order: correct choices as bare `<varequal respident="response" case="No">IDENT</varequal>`, incorrect choices wrapped in `<not><varequal .../></not>`. Added `_is_descendant_of_not(varequal, respcondition)` predicate (walks `getparent()` to the respcondition boundary, returns True if any intermediate tag is `not`) and filters `respcondition.iter("varequal")` through it. Legacy old-shape MA (bare varequals without `<and>`/`<not>`) still reads correctly because none of its varequals have a `<not>` ancestor.
- Fix MATCH `RIGHT_MATCH_BLOCK` placement in `qti_package_maker/engines/blackboard_export_zip/MATCH.py` (`build_MATCH`). The right-side answer pool was appended to the `RESPONSE_BLOCK` flow (one nesting level too deep), so Blackboard Ultra's Import Pool / Import from file imported the item count but rendered an empty bank. It is now appended to the outer `flow class="Block"` as a sibling of `RESPONSE_BLOCK`, matching real Blackboard exports (e.g. `BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch01_Bond_Types_Match4_python`). Verified against Ultra: the three real Blackboard match pools render; the engine's prior output imported empty; the fixed output's presentation skeleton (`QUESTION_BLOCK`, `RESPONSE_BLOCK`, `RIGHT_MATCH_BLOCK` as siblings) now matches the real samples. The reader already tolerated both layouts, so the round-trip stayed green and never surfaced this (91 passed); only a live Ultra import exposed it. Resolves the writer-placement known limitation noted below.
- Align `build_FIB` in `qti_package_maker/engines/blackboard_export_zip/FIB.py` to the real Blackboard FIB feedback wiring. Each per-answer correct `respcondition` now emits no `<setvar>` and two `<displayfeedback>` children: the first `linkrefid="correct" feedbacktype="Response"`, the second `linkrefid` set to that respcondition's own hex-title ident with `feedbacktype="Response"`. A paired `<itemfeedback ident="<hex>">` with a `<solution feedbackstyle="Complete">` body is emitted for each answer so the second `displayfeedback` ref is not a dangling link. FIB still scores via the unchanged `varequal respident="response"` path. Confirmed from real FIB samples.
- Fix MC/MA scoring-link bug in `qti_package_maker/engines/blackboard_export_zip/MC.py` and `MA.py`: `build_MC` and `build_MA` set the `response_lid` ident to a deterministic UUID (`make_ident(... "response_lid" ...)`), but the correct-branch helper emits `<varequal respident="response">`. The literal "response" could not resolve to the UUID ident, breaking the correct-answer link on a live Blackboard import. Both now set the `response_lid` ident to the literal `"response"` (matching NUM/FIB/MULTI_FIB and the real samples, e.g. `BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch03b_General_MC_Full/res00002.dat`); per-choice `label_idents` stay deterministic `make_ident(...)` values. Round-trip stays green (29 passed, 2 skipped).
- Split the 934-line `qti_package_maker/engines/blackboard_export_zip/item_xml_helpers.py` into one builder module per question type, mirroring the `html_selftest` per-type layout. The file is deleted; each `build_<type>` now lives in its own module: `MC.py`, `MA.py`, `MATCH.py`, `FIB.py`, `NUM.py`, `MULTI_FIB.py`. Shared XML primitives (`make_ident`, `build_smart_text`/`build_material_block`/`build_formatted_text_flow`/`build_question_block`, `build_itemmetadata`, `build_outcomes`, `build_incorrect_respcondition`, `build_simple_itemfeedback`, `build_response_label`, `build_render_fib`, `_varequal`, `_not`, `build_correct_setvar_and_feedback`, `format_number`, `_new_item_element`) live in one shared module `common_xml.py`. Consolidated the duplicated per-item skeleton every builder repeated (`_new_item_element` -> `build_itemmetadata` -> `presentation`/outer `flow class="Block"` -> `build_question_block` -> `RESPONSE_BLOCK`) into `common_xml.build_item_skeleton(question_type, absolutescore_max, question_html) -> (item_el, outer_flow, response_block)`, plus `common_xml.start_resprocessing(item_el, max_score)` for the shared `resprocessing`/`outcomes` opening; MA reuses MC's `build_choice_response_lid`. `write_item.py` dispatch now imports the per-type modules by full dotted path (the dispatch functions keep the bare type names `MC`/`MA`/... which would otherwise shadow a short module binding). Pure reorganization with no XML behavior change: the M1-M3 writer-subtree fidelity and round-trip tests pass unchanged with no edited assertions; the only test edit was the import line and four builder call sites in `tests/integration/test_blackboard_export_zip_output.py`. Updated `read_package.py` and `assessment_meta.py` docstrings that referenced the old filename.
- Remove dead code and a dangling re-export in the `blackboard_export_zip` engine: delete the unused `_find_all_flows_by_class` helper from `read_package.py` (zero call sites; only `_find_flow_by_class` is used), and drop the unreferenced `make_ident = item_xml_helpers.make_ident` re-export plus its now-unused `item_xml_helpers` import from `assessment_meta.py`.
- Move the `read_package` import in `engine_class.py` `read_items_from_file` from a local function-body import to the module-level import block and delete the obsolete build-order comment (`read_package.py` exists and imports no engine module, so there is no import cycle).
- Replace planning-scaffolding tags left in permanent comments and docstrings across the engine files and `tests/bb_export_fixtures.py` with durable wording (write dispatcher, write path, forgeability audit, format audit).
- Strip whitespace-only text nodes that sit directly inside table-structure elements in `blackboard_export_zip` question HTML so Blackboard Ultra no longer crashes ("Oops! Something broke.") when the question is expanded. Added `common_xml.sanitize_question_html(html_payload)`, which (only for payloads that contain a `<table>`) parses via `lxml.html` and nulls out whitespace-only text directly inside `<table>`/`<thead>`/`<tbody>`/`<tfoot>`/`<tr>` (the element's leading `.text` and each child's `.tail`); whitespace inside cells (`<td>`/`<th>` content) and all styles/markup are preserved. Payloads without a `<table>` (plain text, or inline markup like `<sup>`/`<b>`/RDKit spans) are returned verbatim so the lxml round-trip never alters non-table content. `common_xml.build_smart_text` calls it before assigning the payload to `mat_formattedtext.text`. Verified on a live Ultra import: the minimal crash content and the real gel-migration NUM both render through the fix, while the same raw content bypassing the fix still crashes. Bare-text payloads (no `<` present) pass through unchanged. The fix keeps the `text-align` styling intact (it removes the whitespace trigger, not the style).

### Removals and Deprecations
- Slim the `blackboard_export_zip` test suite to self-contained, fast pytests because `BB_Export_ZIP/` is not committed and is being deleted, so no test or tool may depend on it. Removed the sample-dependent `tests/integration/test_blackboard_export_zip_reproduction.py` (14 fixture-byte assertions, M0 scaffolding), `tests/integration/test_blackboard_export_zip_scaffolding.py` (9 internal-structure asserts, redundant with the round-trip), `tests/bb_export_fixtures.py` (sample-path helper), and the throwaway `devel/bb_rezip_probe.py` probe (also cleared a bandit B314 finding for its `xml.etree` use). Trimmed `tests/integration/test_blackboard_export_zip_read.py` to the one self-contained unknown-question-type check and `tests/integration/test_blackboard_export_zip_output.py` to the sig-omit and ORDER-skip checks.
- Replace the sample-sweeping round-trip with a self-contained in-code round-trip in `tests/integration/test_blackboard_export_zip_roundtrip.py`: it builds one item of every supported type in memory, writes through the engine to a ZIP in `tmp_path`, reads it back, and asserts behavior-level equality (plus ORDER drop). Runs in ~0.1s and depends on no external data; the prior version walked ~14 `BB_Export_ZIP/` pools and took ~7.5s, over the pytest budget.

### Decisions and Failures
- `.bb-package-sig` is server-computed and NOT reproducible from package contents. Empirical probing (MD5 of manifest, pool `.dat`, and concatenated `.dat` files) all fail to match the real signature. The engine writes no `.bb-package-sig`; the working hypothesis is that a live Blackboard import does not hard-validate it. A live Blackboard/Ultra import remains an optional out-of-band acceptance step that gates nothing in CI.
- NUM and MULTI_FIB encodings confirmed from real samples: NUM uses `response_num`/`Decimal` with `vargte`/`varlte`/`varequal` sibling conditions and no `<and>` wrapper; MULTI_FIB (Fill in the Blank Plus) uses per-blank `respident` keys and an `<and>` of `<or>` conditions.
- MATCH per-prompt branches and NUM correct branch carry no `<setvar>` in real Blackboard exports (conditions matched, not scored additively). Engine follows the real-export shape.
- Confirmed real Blackboard MA encoding: one `<respcondition title="correct">` with `<conditionvar><and>...</and></conditionvar>` listing every choice in original order; correct choices are bare `<varequal respident="response" case="No">IDENT</varequal>`, incorrect choices are wrapped in `<not><varequal .../></not>`; followed by `<setvar variablename="SCORE" action="Set">SCORE.max</setvar>` and `<displayfeedback linkrefid="correct" feedbacktype="Response"/>`. Per-choice penalty branches use `<varequal respident="CHOICE_IDENT" case="No"/>` (empty, no text content). Verified from real MA pools in `BB_Export_ZIP/` (FURAN and Fischer MA).
- Confirmed real Blackboard FIB encoding: each per-answer correct `respcondition` carries no `<setvar>`, two `<displayfeedback>` children (first `linkrefid="correct"`, second `linkrefid` matching the respcondition's own hex-title ident), and a paired `<itemfeedback ident="<hex>">` with `<solution feedbackstyle="Complete">`. FIB scoring routes through the unchanged `varequal respident="response"` path, not `<setvar>`. Verified from real FIB pools in `BB_Export_ZIP/`.
- Pinned the Blackboard Ultra "Oops! Something broke." question-expand crash to a precise, counterintuitive table-whitespace pattern, via ~15 rounds of single-variable Ultra import tests (the renderer is a black box; each hypothesis needed a live import). The crash requires ALL three: (1) the `<table>` carries a `text-align` style (any value; `text-align:left` crashes too), (2) a whitespace-only text node sits directly inside a `<tr>` (e.g. a space between `<tr>` and its first `<td>`, or between cells), and (3) the `<tr>` does NOT end with whitespace before `</tr>` (a "tight close"). It is NOT NUM-specific: MC and MA crash identically; FIB renders the question differently and is unaffected. Proven by single-character minimal cases: `<table style="text-align:center"><tr> <td>x</td></tr></table>` crashes, and removing the leading space, removing the `text-align`, or adding ONE trailing space before `</tr>` each makes it render. Earlier hypotheses were tested and falsified on real bytes and explicitly discarded: a missing `bbmd_asi_object_id` envelope attribute (envelope is constant across pass and fail), exotic named entities such as `&percnt;` (failing items carry none), and `<table>` nested inside `<p>` (lifting the table out of the `<p>` still crashed). The whitespace directly inside a `<tr>` is also invalid HTML (the parser foster-parents it), so the fix removes a genuine defect rather than masking a symptom.
- Tests use inline real-shape XML literals with provenance comments (citing the source pool and item), not committed `.dat` fixture files. A reusable `_write_ma_pool_package` helper builds temp pool packages using the engine's own filename constants (`assessment_meta.POOL_DAT_FILENAME`, `read_package.MANIFEST_FILENAME`), not hardcoded strings. This approach keeps the test suite self-contained and fast, and prevents course content from landing in the repo.
- Known limitations: (1) `item_crc16` drifts across re-import for MC/MA items whose choices carry a strippable prefix. Root cause is core `item_types.MC.__init__` computing `secondary_crc16` from choices before `remove_prefix_from_list` strips them; behavior round-trip still holds via `question_text`. Flagged for a follow-up core fix. (2) The writer nested `RIGHT_MATCH_BLOCK` inside `RESPONSE_BLOCK` while real Blackboard exports place it as a sibling; the reader handles both layouts, so the round-trip stayed safe and never surfaced it, but a live Ultra import rendered an empty bank. Resolved same day (see Fixes and Maintenance): the writer now emits the sibling placement.

### Developer Tests and Notes
- Add three MA reader-fidelity tests to `tests/integration/test_blackboard_export_zip_read.py`: `test_ma_reader_real_shape_multi_correct` (11 choices, 5 correct; derived from FURAN MA pool), `test_ma_reader_real_shape_few_correct` (9 choices, 3 correct; derived from Fischer MA pool), `test_ma_reader_legacy_shape` (bare varequals, old engine shape). All use the `_write_ma_pool_package` helper which builds a temp pool using `assessment_meta.build_pool_wrapper`, `assessment_meta.build_manifest`, and `assessment_meta.POOL_DAT_FILENAME` / `read_package.MANIFEST_FILENAME` so filenames are sourced from the engine, not hardcoded.
- Add MA writer-subtree fidelity test and MA round-trip test to `tests/integration/test_blackboard_export_zip_output.py`: the fidelity test normalizes generated idents and asserts the `<resprocessing>` subtree matches the real Blackboard MA shape; the round-trip asserts recovered `answers_list` equality.
- Add FIB writer-fidelity test (asserts no `<setvar>`, dual `<displayfeedback>`, second `linkrefid` equals the branch title ident, paired `<itemfeedback>`) and FIB round-trip test to `tests/integration/test_blackboard_export_zip_output.py`.
- Add MATCH sibling-placement guard test to `tests/integration/test_blackboard_export_zip_output.py`: asserts `RIGHT_MATCH_BLOCK` and `RESPONSE_BLOCK` share the same parent element by parent identity. The lenient reader could not catch the prior nesting bug; the writer guard now does.
- Add three `sanitize_question_html` tests to `tests/integration/test_blackboard_export_zip_output.py`: `test_question_html_strips_whitespace_inside_table_structure` (the minimal-crash invariant: no whitespace-only text node survives directly inside a table-structure element after `build_smart_text`), `test_question_html_preserves_table_cells_and_styles` (table, `text-align` style, and cell content survive), and `test_question_html_passes_plain_text_through_unchanged`. These replaced two earlier tests written against the discarded `<p><table>` nesting-lift hypothesis.
- Full suite: 2237 passed (was 2183 before the per-type split; the +54 delta is the per-file lint/typing tests gaining six net-new engine modules, not new behavioral tests). MA Ultra closure checkpoint (one-time live import of the regenerated MA item to confirm it displays correct answers and scores) is still pending as a manual pre-archive step.

## 2026-06-09

### Fixes and Maintenance
- Fix 3 failing doc tests. Rewrite `README.md` first paragraph to drop the verbatim repo name `qti_package_maker` and shrink it from 313 to under 250 chars so the GitHub About-field tests (`tests/test_readme_first_paragraph.py`) pass. Fix all `tests/test_markdown_links.py` failures: in `docs/FILE_STRUCTURE.md` point the license link to the real `LICENSE.LGPL_v3`, rename the `source_me_for_testing.sh` link to `source_me.sh`, and change three redundant `[docs](../docs)` links to `[docs](.)`; in `docs/CHANGELOG.md` strip redundant `../docs/` traversal from two same-folder links and convert two untracked `ULTRA/` links to code spans; in `docs/BLACKBOARD_ULTRA_NOTES.md` convert 12 links targeting untracked `ULTRA/`, `output/`, and `tools/` probe artifacts to code spans (they 404 on GitHub). Full suite 1242 passed.

### Behavior or Interface Changes
- Bump CalVer version from 26.03 to 26.06 in `VERSION` and `pyproject.toml` because the html_selftest engine output changed (FIB f-string fix, mojibake escape_non_ascii widening to all non-ASCII, feedback-pill CSS, disabled Check Answer button state, and larger choice controls). The bump signals downstream consumers that cached 26.03 self-test fragments are stale and should be regenerated.

## 2026-06-08

### Additions and New Features
- JS/emitter polish pass (WS-B): feedback pill now engages on every answer check. In all 7 question-type emitters (`add_MC.py`, `add_MA.py`, `add_FIB.py`, `add_MULTI_FIB.py`, `add_NUM.py`, `add_MATCH.py`, `add_ORDER.py`) the `checkAnswer_<crc>` body now sets `resultDiv.className` to `qti-feedback-result qti-feedback-success` on full-correct or `qti-feedback-result qti-feedback-error` on wrong/partial/invalid; neutral `qti-feedback-result` on empty/prompt states. Inline `style.color` assignments removed in favor of CSS classes. Check Answer button is disabled (`checkBtn.disabled = true`) on full-correct so the question appears resolved; reset/clear paths (`clearSelection_<crc>` and `resetGame_<crc>` in `javascript_functions.py`) re-enable the button and reset the pill class to neutral. `add_clear_selection_button` now emits `qti-btn-reset` class (ghost/secondary) instead of the primary class. Non-color accessibility markers added as CSS `::before` generated content in `html_functions.py`: `.qti-feedback-success::before { content: "[+] "; }` and `.qti-feedback-error::before { content: "[x] "; }` (ASCII only; no textContent change). result textContent strings are byte-for-byte unchanged for bp-website classifier compatibility (`CORRECT`, `incorrect`, `Total Score: X out of Y`, `Correct positions: X of Y`, `Correct: X of Y`). All 1194 tests pass.
- Visual polish pass on html_selftest theme CSS in `qti_package_maker/engines/html_selftest/html_functions.py`. All changes are additive CSS + minimal markup; no result strings, element IDs, or function names changed. (1) Enlarged radio/checkbox inputs: `.qti-selftest ul[id^="choices_"] > li > input[type="radio"/"checkbox"]` now `width: 1.4em; height: 1.4em; flex-shrink: 0; accent-color: var(--qti-btn-bg)`, with per-li `min-height: 40px` and `padding: 6px 4px` for touch-friendly tap targets. (2) Feedback pill: `add_result_div` now emits `class='qti-feedback-result'` instead of a monospace inline style. New `.qti-feedback-result` CSS sets `display: inline-block; border-radius: 12px; padding: 4px 12px; font-family: inherit; font-weight: 600; margin: 8px 0`. Existing `.qti-feedback-success` and `.qti-feedback-error` updated to match the pill shape (same `border-radius: 12px; padding: 4px 12px; inline-block`); JS task targets these classes unchanged. (3) Styled buttons: `.qti-btn` now solid filled primary (`background: var(--qti-btn-bg, #3a5acd); color: var(--qti-btn-fg, #ffffff); border: none; border-radius: 4px; padding: 8px 20px`); `.qti-btn-reset` ghost secondary (`border: 1px solid var(--qti-btn-reset-border)`). (4) Dark-mode inputs: `--qti-input-bg` set to `#2a2a2a` with `--qti-input-fg: #e0e0e0` in the `prefers-color-scheme: dark` and `[data-md-color-scheme="slate"]` blocks; button vars similarly updated. (5) Responsive media: `.qti-selftest canvas, .qti-selftest img { max-width: 100%; height: auto; }` to prevent RDKit canvases overflowing on mobile. All 1192 tests pass.

### Fixes and Maintenance
- Add `:disabled` CSS styling for the Check Answer button in `qti_package_maker/engines/html_selftest/html_functions.py`. After a fully-correct answer the JS sets `checkBtn.disabled = true`, but there was no CSS for the disabled state so the button stayed full-blue. New rules `.qti-btn:disabled, .qti-btn[disabled]` set `opacity: 0.55; cursor: not-allowed; filter: none` and swap the background/foreground to muted greys via new CSS variables `--qti-btn-disabled-bg` and `--qti-btn-disabled-fg`. Light theme uses `#aaaaaa`/`#eeeeee`; dark theme (`@media prefers-color-scheme: dark` and `body[data-md-color-scheme="slate"]`) uses `#555555`/`#aaaaaa`. The `body[data-md-color-scheme="default"]` block also gets the light-theme disabled vars for completeness. Enabled `.qti-btn` appearance and the ghost `.qti-btn-reset` are unchanged. Output remains pure ASCII. All 1194 tests pass.
- Fix mojibake in html_selftest engine: rename `escape_non_iso_8859_1` to `escape_non_ascii` in `qti_package_maker/engines/html_selftest/html_functions.py` and widen the escaping range from codepoints > U+00FF to ALL non-ASCII (> U+007F) using `text.encode("ascii", "xmlcharrefreplace").decode("ascii")`. Previously, Latin-1 characters such as non-breaking space (U+00A0), plus-minus (U+00B1), and middle dot (U+00B7) were emitted as raw multi-byte UTF-8 sequences that rendered as A-circumflex mojibake under any non-UTF-8 charset declaration. Update the sole call site in `write_item.py` (`_wrap_selftest_html`) to use the new name. Also change the literal `&nbsp;` placeholder in `add_result_div` to the numeric entity `&#160;` so every byte of generated output remains below 0x80. Add 5 focused tests in `tests/unit/test_html_selftest_encoding.py` verifying: Latin-1 block chars produce `&#160;`/`&#177;`/`&#183;`; plain ASCII is unchanged; `None` input returns `""`; `add_result_div` contains `&#160;` not `&nbsp;`; full MC output passes `.isascii()`. All 1192 tests pass.
- Fix `add_FIB.py` line 22: replace `{normalized_answers!r}` with `json.dumps(normalized_answers)` in the JS array emitter. Python repr of a list uses single-quoted strings and Python escaping, which produces invalid JS when answers contain a single quote, backslash, or non-ASCII character (parse-time SyntaxError, same blast radius as the f-string bug fixed 2026-06-07). `json.dumps` produces a standards-conformant double-quoted array literal that is always valid JS. Add `import json` at the top of `add_FIB.py` following module import-ordering style.

### Developer Tests and Notes
- Style fixes in `tests/unit/test_html_selftest_contract.py` (move module docstring to top before imports, regroup `import pytest` under `# PIP3 modules`) and `tests/unit/test_html_selftest_output.py` (replace fragile `[0]` array-line lookup with `next(..., None)` plus a clear `assert ... is not None` message); behavior unchanged.
- Add `test_fib_js_answers_array_is_valid_js_with_special_chars` to `tests/unit/test_html_selftest_output.py`: calls `generate_javascript` with an answer containing a single quote (`"it's correct"`) and an ASCII answer, extracts the array assignment line, and asserts the RHS starts with `["` (double-quoted JSON) rather than `['` (Python repr). Behavioral check: if the emitter reverts to repr, the test fails. Full suite 1187 passed.
- Add `tests/unit/test_html_selftest_contract.py` with 15 regression-guard tests locking the result-string contract that bp-website's `selftest_progress.js` runtime depends on. Tests cover: element-ID patterns (`question_html_<crc>`, `result_<crc>`, `checkAnswer_<crc>`) for all 7 question types; literal `'CORRECT'` emitted by MC, MA, NUM, FIB, and MULTI_FIB (full-correct path); `Total Score: ${score} out of ${possible}` emitted by MATCH; `Correct positions: ${correct} of ${total}` emitted by ORDER; `Correct: ${correctCount} of ${inputs.length}` emitted by MULTI_FIB (partial-correct path). Note: MULTI_FIB full-correct emits `'CORRECT'` (same as MC/MA/NUM/FIB), not the `Correct: X of Y` form. Full suite 1186 passed in 5.13s.

## 2026-06-07

### Fixes and Maintenance
- Fix `add_FIB.py` line 28: add missing `f` prefix so the emitted JS correctly references `fibAnswers_<crc>.includes(userAns)` instead of the literal string `fibAnswers_{crc16_text}.includes(userAns)`. Without this fix, every FIB "Check Answer" button threw a ReferenceError and could never mark an answer correct.
- Fix `add_FIB.py`: change hardcoded `'green'`/`'red'` result colors to CSS theme vars `var(--qti-success-fg, #008000)` and `var(--qti-error-fg, #9b1b1b)` to match all other html_selftest question types.

### Developer Tests and Notes
- Add `test_fib_js_uses_crc_not_literal_placeholder` and `test_fib_js_uses_theme_var_colors` to `tests/unit/test_html_selftest_output.py` asserting the FIB JS emitter outputs the correct crc-substituted function name and theme-var colors. Both tests pass; full suite 1171 passed.

## 2026-04-14

### Additions and New Features
- Add `docs/BLACKBOARD_ULTRA_NOTES.md`, the empirical contract for what Blackboard Ultra accepts, rewrites, and destroys on QTI 2.1 import/export. Derived from one manual round trip of `output/ultra_probe.zip` through an Ultra sandbox; re-export preserved in `ULTRA/ultra_probe-roundtrip/`.
- Patch 6 (Ultra engine scaffolding): implement complete item writer pipeline for Blackboard Ultra QTI 2.1. Add `qti_package_maker/engines/bb_ultra_qti_v2_1/item_xml_helpers.py` with Ultra-native QTI element builders (Ultra-shaped responseDeclaration with cardinality="multiple" for MC/MA, unpadded answer_N identifiers, double-div itemBody wrapping, SCORE+FEEDBACKBASIC+MAXSCORE outcomes). Add `qti_package_maker/engines/bb_ultra_qti_v2_1/write_item.py` with per-item-type dispatch (MC, MA, FIB, NUM, MULTI_FIB, MATCH; NO ORDER). Add `qti_package_maker/engines/bb_ultra_qti_v2_1/assessment_meta.py` manifest and question_bank builders with canonical Ultra resource structure and 5-digit zero-padded item identifiers. Add `qti_package_maker/engines/bb_ultra_qti_v2_1/engine_class.py` extending BaseEngine with full ZIPing pipeline: calls `type_normalize.normalize_items()` to drop ORDER items with warnings, dispatches to write_item per type, writes items to `qti21/assessmentItemNNNNN.xml`, writes manifest and question_bank, zips with `csfiles/home_dir/` empty directory. Engine auto-discovered by `engine_registration.py`. Add 4 comprehensive integration tests in `tests/integration/test_ultra_engine_smoke.py` covering single MC item, multi-type bundle with ORDER drop verification, manifest structure validation, and question_bank structure validation (all 4 tests pass).
- Milestone 10 partial (CLI + docs + tests): Add `--ultra` (`-u`) CLI flag to `tools/bbq_converter.py` for easy access to the `bb_ultra_qti_v2_1` engine (also available as `--qti21-ultra` long form). Add new `bb_ultra_qti_v2_1` section to `docs/ENGINES.md` documenting the engine, CLI flag, supported item types (MC, MA, FIB, NUM, MULTI_FIB, MATCH), unsupported types (ORDER), and key differences from the Learn engine (HTML sanitization, heading level shift, no column width control, underline loss, no inline images, Hot Spot non-round-trip stability). Update capability tables in `docs/ENGINES.md` to include the new engine (can_write: yes, can_read: no) and its item type support matrix. Add integration test `test_bbq_converter_ultra_flag()` to `tests/integration/test_bbq_converter_cli.py` verifying the `-u` flag produces a valid output ZIP (test passes).

### Fixes and Maintenance
- Ultra engine: fix a false positive in `_is_hiding_style` that was dropping every table cell with `background-color: white` (or `#ffffff`, or `border-color: white`). The check was substring-based and matched `color:white` inside `background-color:white`, nuking cell content. Rewrite the matcher to split the style on `;`, split each declaration on `:`, and require an EXACT property-name match (e.g. `prop == "color"`). Value checks remain substring so `1px !important` still matches. Two new regression tests: one that asserts every variant of white-background declaration survives, and one that passes a plain Michaelis-Menten-shaped data table through and confirms every cell value is preserved.
- Ultra engine: add a `_drop_hidden_elements` phase to `html_sanitize.py` that runs BEFORE the style-strip phase and drops (tag + content) any element whose `style=` attribute contains a CSS-hiding signature (`font-size: 1px`, `font-size: 0`, `color: white`, `color: #fff`, `color: #ffffff`, `display: none`, `visibility: hidden`, `opacity: 0`). Reason: anti-cheat helpers in the upstream biology-problems repo sprinkle `<span style='font-size: 1px; color: white;'>word</span>` into question text as a distribution-tracking deterrent. Ultra strips every style attribute on import, which would promote these hidden words to visible garbage and destroy the question. The new phase drops them in-engine so the cheat-deterrent behavior is simply lost (rather than corrupted) on the Ultra path. Each dropped element is replaced with a single space so adjacent words do not collapse together (`The<span>cheat</span>following` -> `The following`, not `Thefollowing`); the anti-cheat pipeline emits hidden spans as replacements for inter-word spaces, so silent removal was collapsing neighbors. Add four pytest cases: the canonical anti-cheat span, a sweep of CSS-hide variants, the word-boundary preservation check, and an idempotence check (space replacement must not keep growing on repeated sanitization).
- Ultra engine: thread `package_name` into `assessment_meta.generate_question_bank()` and use a humanized form of it as the `assessmentTest/@title` instead of the hardcoded literal `"Test Bank"`. Humanizer replaces underscores with spaces but keeps hyphens (which often carry meaning, like the trailing `-Km` in `michaelis_menten_table-Km`). The Ultra UI now shows the actual package name as the upload title.

### Decisions and Failures
- **`<pre>` is functionally equivalent to `<p>` in Ultra.** The `<pre>` tag survives round trip, but every whitespace semantic is destroyed: newlines collapse to spaces, runs of spaces collapse to single spaces, tabs collapse to single spaces. Confirmed by probe items 1 (pre_alignment), 2 (pre_vs_p), and 7 (whitespace_stress). Kills the planned `<pre>` + tabulate table strategy entirely.
- **`&#xa0;` runs and `<br/>` are the only reliable layout primitives.** Five-nbsp runs and five-br runs survive round trip byte-for-byte (probe items 3 and 4). The new `bb_ultra_qti_v2_1` engine will use `<p>` with nbsp padding and `<br/>` row separators as its sole table strategy - no fallback ladder.
- **`<img>` is structurally broken on Ultra re-export.** Probe item 15 showed Ultra replaces the `src` with a null-file WebDAV stub, drops the referenced PNG from `csfiles/home_dir/`, and turns the self-closing `<img/>` into a wrapper that absorbs subsequent siblings as children. The engine will strip `<img>` unconditionally.
- **All CSS is stripped.** `style=` attributes on spans and blocks, `<style>` tags, and `class=` attributes are all removed on re-export (probe item 14). No narrow property allowlist survives; even the text color and font size the WYSIWYG editor shows while authoring do not round-trip. CSS is a non-feature.
- **Ultra shifts heading levels down by 1.** `<h3>` becomes `<h4>`, `<h4>` becomes `<h5>` (probe item 13). The engine will emit `<h4>`/`<h5>` directly.
- **`<hr/>`, `<blockquote>`, and `<kbd>` are stripped.** Content of `<blockquote>` and `<kbd>` is preserved, wrapper removed. `<hr/>` disappears entirely.
- **Deprecated presentational attributes are stripped.** `border`, `cellpadding`, `cellspacing`, `align`, `width`, `bgcolor` all removed from `<table>`, `<tr>`, `<th>`, `<td>` (probe item 8). Table tags survive structurally but render as a single-column vertical stack - not usable for layout.
- **`<b>`, `<i>`, `<u>` are rewritten.** `<b>` to `<strong>`, `<i>` to `<em>`, `<u>` to an attribute-less `<span>` (underline visually lost).

### Fixes and Maintenance
- Purge and consolidate Ultra engine pytests to match [PYTHON_STYLE.md](PYTHON_STYLE.md) PYTEST guidance. Collapse the seven new/changed test files (1881 lines, 74 tests) to five files (572 lines, 45 tests) by parametrizing granular cases, dropping brittle collection-size / hardcoded-identifier / navigation-mode asserts, merging smoke and full integration suites into `tests/integration/test_ultra_engine.py`, deleting `tests/integration/test_existing_engines_unchanged.py` (duplicate of `tests/test_all_engines.py`), and removing standalone idempotence tests covered by a single complex-mixed-case test. Swap `len(match1.prompts_list) == 4` (a trivial collection-size check) for a content assertion that every original ORDER label survives the MATCH shuffle. All 45 consolidated tests pass; pyflakes clean.
- Patch 7 (Ultra engine manifest alignment audit): audit the `bb_ultra_qti_v2_1` engine's manifest builders (`assessment_meta.py`) against canonical Ultra re-export shapes from the probe round-trip (`ULTRA/ultra_probe-roundtrip/`). Test `generate_manifest(2)` and `generate_question_bank(2)` in isolation by calling functions directly and comparing serialized output against canonical files. Finding: manifest builders produce structurally identical XML. Differences are formatting only (lxml pretty_print vs minified) and assessmentTest @title (generic "Test Bank" vs probe-specific "Ultra Probe"), both acceptable and documented. No code changes to manifest builders required. Pyflakes clean. Note: full end-to-end smoke test is blocked by pre-existing M6 defect in `compat_gate.py` where the allowed_tags set uses lowercase names but QTI XML has camelCase tags; documented in BLACKBOARD_ULTRA_NOTES.md as a known M8 issue.
- Append "Generated manifest vs. canonical reference" subsection to [BLACKBOARD_ULTRA_NOTES.md](BLACKBOARD_ULTRA_NOTES.md) documenting M7 audit methodology, findings (no structural differences), acceptable differences rationale, and a new "Known issues" section documenting the pre-existing M6 compat_gate defect.
- Patch 8 (Ultra engine compat_gate): implement `qti_package_maker/engines/bb_ultra_qti_v2_1/compat_gate.py` with `UltraCompatibilityError` exception class and `validate_assessment_items()` function. Gate enforces eight hard-fail rules (XML must round-trip through lxml.etree; correctResponse values must match simpleChoice identifiers; no style= or class= attribute residue; no script/style/img elements; no disallowed tags in itemBody; outcomeDeclaration with identifier="SCORE" must be present). Gate enforces three warn rules (unknown tags logged but not blocked; cell text >1000 chars warned; empty choiceInteraction warned). Gate accepts a list of etree.Element assessmentItem nodes and returns a list of warning strings; raises UltraCompatibilityError on hard-fail. Wire gate into `engine_class.py`'s `save_package()` to validate all items after `write_assessment_items()` but before ZIP packing. Add 10 comprehensive pytest test cases in `tests/test_ultra_compat_gate.py` (all pass) covering well-formed pass, dangling correctResponse hard-fail, style/script/img/disallowed-tag hard-fails, missing SCORE hard-fail, unknown attribute warn, oversized cell warn, empty choiceInteraction warn. Pyflakes clean.

### Developer Tests and Notes
- Patch 9 (M9 integration + regression guards): Add `tests/integration/test_existing_engines_unchanged.py` (11 tests) covering regression detection for all pre-existing engines: `blackboard_qti_v2_1`, `canvas_qti_v1_2`, `bbq_text_upload`, `html_selftest`, `exam_yaml`, `human_readable`, `moodle_aiken`, `text2qti`, `okla_chrst_bqgen`. Uses pragmatic property-based approach (not brittle byte-for-byte snapshots) to detect structural regressions: verifies each engine can output a 3-item fixture (MC, FIB, NUM), parses output, and validates presence of key structural elements (imsmanifest.xml, item files, ZIP validity). Includes test for `bbq_converter.py` default flag routing (verifies `-1` flag works without Ultra engine becoming default). All 11 tests pass. Add `tests/integration/test_ultra_engine_full.py` (8 tests) as comprehensive Ultra integration test suite: tests full item-type range (MC, MA, FIB, NUM, MULTI_FIB, MATCH, ORDER with skip), manifest XML validity, SCORE outcome declarations, question_bank item reference counts, csfiles directory presence, correctResponse identifier validity, style attribute stripping in itemBody, and round-trip XML re-parsing invariant. All 8 tests pass. Verify `test_all_engines.py` already includes the new `bb_ultra_qti_v2_1` engine via auto-registration (no code changes required). Test suite now includes 51 existing Ultra unit tests + 4 smoke tests + 8 full integration tests + 11 regression guard tests = 74 new/extended tests for Ultra. Pyflakes clean across all test files.
- Add `tools/build_ultra_probe.py`, a throwaway script that emits `output/ultra_probe.zip` containing 15 small MC probe items targeting one Blackboard Ultra HTML/structural sanitizer dimension each (`<pre>`, `&nbsp;` columns, bare `<table>`, cell structure variants, whitespace, inline formatting, lists, headings, entities, `style=` and `<style>`, `<img>`). The ZIP is cloned from the shape of `ULTRA/manually-created-ultra-question/` (compact manifest with `csm`/`imsqti` namespaces, `qti21/question_bank00001.xml` test file, `csfiles/home_dir/probe_tiny.png` hand-built 67-byte PNG). First milestone of the new `blackboard_qti_v2_1_ultra` engine plan; the probe is the input to one manual Ultra round trip that will lock the table strategy and allowed-tag set.
- Round-trip output of the probe ZIP through the Ultra sandbox is preserved verbatim at `ULTRA/ultra_probe-roundtrip/`. All 15 items imported and re-exported as well-formed XML (every item parses under `lxml.etree`), including the structurally broken item 15 wrapper.
- Patch 3 (Ultra engine `type_normalize` stage): implement `qti_package_maker/engines/bb_ultra_qti_v2_1/type_normalize.py` with `normalize_items()` function supporting three ORDER-mapping policies (`skip`, `mc`, `match`), plus `UltraUnsupportedTypeError` for future extensibility. Add 11 pytest test cases in `tests/test_ultra_type_normalize.py` covering all policies, MC/MA/MATCH/NUM/FIB/MULTI_FIB pass-through, permutation correctness, and deterministic MATCH shuffling. All tests pass; pyflakes clean.
- Rewrite `docs/BLACKBOARD_ULTRA_NOTES.md` from scratch to reflect the post-second-probe findings. Removes the retracted nbsp-only table strategy and the "tables do not render" misdiagnosis. Adds executive summary for non-technical readers, Michaelis-Menten root cause (self-closing `<colgroup width="160"/>` HTML5 parser bug), supported question types table, Hot Spot round-trip failure, SVG non-support, canonical Ultra-native image embedding format from `ULTRA/image_test/`, and a Learn-to-Ultra porting forecast table. Suitable for sharing with non-technical stakeholders.
- Patch 4 (Ultra engine `html_sanitize` stage): implement `qti_package_maker/engines/bb_ultra_qti_v2_1/html_sanitize.py` with `sanitize_fragment()` function. Core operation: re-serialize every HTML fragment through `lxml.html.fromstring` + `lxml.html.tostring` to repair self-closing non-void tags (`<colgroup width="160"/>` -> `<colgroup></colgroup>`, the root cause of Michaelis-Menten first-import collapse). Enforces Ultra's empirical tag/attribute allowlist: keep `p`, `div`, `span`, `br`, `em`, `strong`, `sub`, `sup`, `code`, `ul`, `ol`, `li`, `h4`, `h5`, `table`, `tbody`, `tr`, `th`, `td`, `colgroup`, `col`, `a`; rewrite `b`->`strong`, `i`->`em`, `u`->`span`, `h1`/`h2`/`h3`->`h4`, `h4`->`h5` (with idempotence guard), `pre`->`p`; unwrap `blockquote`, `kbd`, and unknown tags; drop `script`, `style`, `img` with content. Strip attributes: `style`, `class`, `id`, `cellpadding`, `cellspacing`, `bgcolor`, `border`, `align`, `width`, `height`, `color`, `face`, `valign`, all event handlers, all namespaced attributes; preserve `<a href>` only. Add 30 comprehensive pytest cases in `tests/test_ultra_html_sanitize.py` covering colgroup repair, tag rewrites, attribute stripping, unwrapping, dropping, idempotence (all 30 cases pass including idempotence tests). No pyflakes errors.

## 2026-04-02

### Additions and New Features
- Add `exam_yaml` write-only engine that exports an ItemBank to exam YAML format for printable ODT exam generation. Supports MC, MA, MATCH, ORDER, NUM, FIB, and MULTI_FIB item types. This is an intentionally lossy export: answer keys, scoring metadata, and section structure are not preserved. Inline HTML tags (`<sub>`, `<sup>`, `<b>`, `<strong>`, `<i>`, `<em>`) and HTML entities (`&Delta;`, `&deg;`, etc.) are passed through verbatim.

### Fixes and Maintenance
- Refactor test suite to match `docs/PYTHON_STYLE.md` guidelines across all test files.
- Convert `from X import Y` and aliased `from X import Y as Z` imports to `import X` module style across ~30 test files.
- Remove try/except block in `test_all_engines.py`; engines return None for unsupported types instead of raising.
- Replace brittle `len(bank) == N` collection size assertions with behavioral checks (`len(bank) > 0`, `len(bank) > 1`, etc.) across unit and integration tests.
- Replace brittle `item_type == __class__.__name__` assertion in `test_item_types.py` with property-based check.
- Convert spaces to tabs in `test_color_wheel_next_gen.py`.
- Split oversized `test_write_html_color_table_cam16_debug` (12+ assertions) into 6 focused test functions.

## 2026-04-01

### Additions and New Features
- Add `_detect_tablefmt()` and `_has_visible_border()` helpers in `string_functions.py` that inspect HTML table border attributes to choose the appropriate tabulate format: `"fancy_grid"` for cell-level visible borders, `"plain"` for `border="0"`, and `"fancy_outline"` for table-level border with collapse.
- Add four unit tests for border-aware tablefmt detection: visible cell borders, cell `border: 0` (metabolic pathway pattern), `border="0"` attribute, and border-collapse.

### Fixes and Maintenance
- Fix `_html_table_to_text()` rendering borderless HTML tables (e.g., metabolic pathway diagrams) with box-drawing grid lines. Tables with `border: 0` on cells now correctly use plain format instead of `fancy_grid`.

### Decisions and Failures
- Reviewed all `tablefmt` calls across the codebase (5 call sites). Console display calls in `item_bank.py` and `engine_registration.py` all use `"fancy_outline"` consistently. No consolidation needed; adding a shared constant would add indirection without benefit.

## 2026-03-30

### Behavior or Interface Changes
- Rename changelog section headings to match REPO_STYLE.md spec: `Added` to `Additions and New Features`, `Changed` to `Behavior or Interface Changes`, `Fixed` to `Fixes and Maintenance`, `Removed` to `Removals and Deprecations`, `Chore` to `Fixes and Maintenance`.
- Replace backslash-escaped quotes with alternating quote styles in `html_functions.py`.
- Add return type hints to public functions in `item_types.py`, `item_bank.py`, `string_functions.py`, and `html_functions.py`.
- Refactor `from`/`as` imports to direct module imports in `test_multi_engine_roundtrip.py` and `test_html_selftest_output.py`.
- Convert 3-space indentation to tabs in `rcp_debug_plots.py`.
- Bump version from 26.02 to 26.03.
- Fix version mismatch check in `bbq_converter.py` to normalize PEP 440 versions before comparing (e.g., `26.03` vs `26.3`); use `packaging.version.Version` for proper normalization.
- Add editable-install sync check to `devel/submit_to_pypi.py` that detects stale `pip install -e .` metadata before running pytest, preventing confusing version mismatch failures.
- Add bold choice letters (A., B., C., etc.) to html_selftest MC and MA labels.
- Wrap html_selftest choice text in a `<span>` so `<sub>` and `<sup>` tags render as proper subscripts and superscripts inside flex labels.
- Add visible-text-length check to `determine_choice_layout_class()` so choices longer than 50 visible characters force vertical layout instead of grid.
- Strip HTML tags and unescape entities before measuring choice text length for layout decisions.
- Remove `__version__` assignment from `qti_package_maker/__init__.py`; version check in `bbq_converter.py` now uses `importlib.metadata.version()` directly.
- Remove re-exports and `__all__` from `color_theory/__init__.py`; all consumers already import submodules directly.
- Rename `color_theory/main.py` to `color_theory/rcp_debug_plots.py` to reflect its role as a dev visualization script.
- Move `matplotlib`, `numpy`, and `scipy` from `pip_requirements.txt` to `pip_requirements-dev.txt` (only used in `rcp_debug_plots.py`).
- Remove incorrect `colour` entry from `pip_requirements.txt`; add `"colour": "colour-science"` alias to `test_import_requirements.py`.

## 2026-02-07

### Additions and New Features
- Add temporary root note `TEMP_RDKit_QTI_IMPORT_NOTES.md` summarizing observed RDKit/script import behavior across Canvas QTI 1.2, Blackboard QTI 2.1, Blackboard BBQ text, and ADAPT QTI 1.2.

## 2026-02-06

### Behavior or Interface Changes
- Add extra blank-line spacing between major XML sections in Canvas QTI v1.2 and Blackboard QTI v2.1 outputs to improve manual readability.
- Add unit assertions for QTI spacing patterns and reinforce BBQ text upload single-line output behavior.

## 2026-02-05

### Additions and New Features
- Add Agent Self-Check Questions section to AGENTS.md with key questions agents should answer after reading repository guidelines.
- Add unit tests for adaptive grid layout: test_determine_choice_layout_class, test_html_selftest_mc_adaptive_grid_classes, test_html_selftest_ma_adaptive_grid_classes.

### Behavior or Interface Changes
- Add adaptive CSS Grid layouts for html_selftest MC/MA choices based on choice count.
- Use CSS Grid auto-fit with minmax to automatically arrange choices based on rendered width.
- Apply compact grid (min 150px columns) for 4-5 choices, standard grid (min 200px) for 6+ choices.
- Keep vertical layout for 2-3 choices for optimal readability.

## 2026-02-03

### Behavior or Interface Changes
- Align html_selftest MC/MA choice inputs and labels with flex layout styling.
- Increase html_selftest input font size and apply theme input styling to FIB inputs.

## 2026-02-02

### Additions and New Features
- Add tests/test_strip_prefix.py to guard decimal handling in prefix stripping helpers.
- Expand decimal cases in tests/test_strip_prefix.py for numeric prefixes like 0.0089 and 12.5.

### Behavior or Interface Changes
- Restrict prefix dot matching to non-decimal cases to preserve numeric answers.
- Fix YY.MM regex parsing in devel/bump_version.py for short prerelease versions.
- Allow bare YY.MM versions in bump_version validation.
- Treat YY.MM and YY.MM prerelease strings as version candidates in bump_version scanning.
- Force VERSION file updates even when the existing value is not a recognized version.
- Allow --update-all --set-version to proceed when multiple versions are discovered.
- Skip pip upgrades in devel/submit_to_pypi.py to avoid Homebrew-managed pip failures.

## 2026-01-19

### Behavior or Interface Changes
- Replace yaml.load usage with a safe loader path that preserves duplicate key checks.
- Update unit tests to use pytest tmp_path instead of hardcoded /tmp paths for Bandit compliance.
- Escape non-ISO-8859-1 characters in html_selftest HTML output with numeric entities.
- Add tests dir to sys.path in pytest conftest to allow local test imports.
- Use git rev-parse to determine REPO_ROOT in pytest conftest.
- Scope html_selftest MATCH drag-and-drop initialization by item id to avoid multi-item collisions.
- Scope html_selftest MATCH/ORDER dropzone queries to each item container and add output tests for scoping.
- Use append_const for bbq_converter format shortcuts so flags like -s do not suggest an argument.

## 2026-01-16

### Behavior or Interface Changes
- Refresh README.md to a concise overview with a quick start and curated documentation links.
- Refresh docs/INSTALL.md and docs/USAGE.md to minimal, evidence-based stubs.
- Add docs/CODE_ARCHITECTURE.md and docs/FILE_STRUCTURE.md and link them from README.md.
- Prune README.md documentation links to the required core set plus a short "More docs" list.
- Remove shebangs from non-executable color_theory modules to satisfy shebang_not_executable lint.
- Fix mixed-indentation lines in item_types, anti_cheat, and text2qti read_package.
- Remove invalid python shebangs from non-executable modules flagged by lint.
- Remove shebangs from pytest modules flagged as non-executable.
- Remove shebangs from additional non-executable engine/test modules flagged by lint.
- Remove remaining non-executable shebangs from unit tests to satisfy shebang alignment checks.

## 2026-01-15

### Behavior or Interface Changes
- Simplify `color_wheel.py` public API to single function `generate_color_wheel()`.
- Switch default color wheel backend from legacy to CAM16.
- Restore public color wheel shims for named wheels and legacy helpers, backed by CAM16 output.
- Remove unused imports from `next_gen.py` and `generator.py`.
- Update color wheel tests to import internal functions directly from source modules.
- Fix bugs in `main.py`: typo in `_validate_hsl` error message, undefined `l` variable, remove dead `sys.exit()` call.
- Remove unused `pytest` imports from test files.

### Fixes and Maintenance
- Resolve all 46 pyflakes errors (reduced to 0).

## 2026-01-14

### Behavior or Interface Changes
- Replace Unicode box-drawing and emoji in `docs/CODE_DESIGN.md` with ASCII equivalents.
- Replace checkmark/cross table markers with yes/X in `docs/ENGINES.md`.
- Replace Unicode status symbols in test output strings and use ASCII-safe escapes for sub/superscript mappings.

## 2026-01-13

### Behavior or Interface Changes
- Resolve README merge markers and restore the question types/engine sections.
- Make README ISO-8859-1 compatible by replacing non-ASCII table symbols.
- Fix README formatting in the Python API example block.

## 2026-01-03

### Additions and New Features
- **Planning**: Add `COLOR_WHEEL_REFACTOR_PLAN.md` with a perceptual color sampling plan and visual test notes.
- **Next-gen experiments**: Add `qti_package_maker/common/color_wheel_next_gen.py` for OKLCH-based color wheel experiments.
- **Tests**: Add pytest coverage for next-gen color wheel utilities.

### Behavior or Interface Changes
- **Refactor plan & docs**: refine hue spacing and fixed lightness bands; define even chroma via shared min max chroma; add working history; add design corrections and per-wheel policy guidance; add/remove xdark/normal policy drafts per scope; replace plan with CAM16-based plan and rollout steps; add dependency notes; keep CAM16 opt-in until default; add Remaining Items.
- **Module structure & compatibility**: move color wheel modules into `color_wheel/` with shims; expand shim exports for tests; remove OKLCH next-gen module/tests while keeping legacy in `legacy_color_wheel.py`; add deprecation warning and update tests to import legacy directly; move implementations to `color_theory/` with legacy facade; add `generate_color_wheel` facade; add legacy parity + CAM16 smoke tests.
- **CAM16 implementation & tuning**: select `colour-science` and wire CAM16 adapter/skeleton; adjust J targets (add very_dark, lighten dark/light, xdark/normal tweaks); boost dark saturation and soften light/pastel output; rotate wheels so hue 1 anchors to true red; emit legacy red RGB distance in HTML; use American spelling (except `colour-science`).
- **Debug & inspection tooling**: add CAM16 debug HTML; anchor to best-red offsets; make deterministic; add XKCD name labels; add CAM16-UCS radius/gamut margin/per-hue max-M utilization; remove M/gamut_limit from debug; add UCS target diagnostics; add control selection indicator; add clamp_reason and prefer per-hue M_max caps for UCS control; add CAM16 spec helper and J/M/Q range tests.
- **Light UCS control**: remove mode-level M caps for UCS-driven modes and skip max-M anchoring in debug/HTML for UCS modes.
- **Validation**: enforce shared_m_quantile in [0.0, 1.0] and add pytest coverage for invalid quantiles.
- **Release tooling**: remove repo-derived CLI args from `devel/submit_to_pypi.py`, require VERSION file, and fix rich stderr output.
- **Release tooling**: test installs now pin the exact version (with --pre when needed) and project URLs use canonicalized names.
- **Release tooling**: always check for existing versions; `--version-check` now runs the check and exits.
- **Release tooling**: remove clean/upgrade/test-install/open toggles and index/repo URL overrides; these steps now run unconditionally.
- **Release tooling**: add pre-checks (PEP 440 version parse, requires-python, git clean/main, version tag, twine, pytest when installed, and dist empty after clean).
- **Release tooling**: require `main` to be fully synced with `origin/main` (fetch + ahead/behind check).
- **Release tooling**: add `--build-only` mode and log build output to `build_output.log`.
- **Release tooling**: add index reachability check before version lookup.
- **Release tooling**: include prereleases when checking index versions.
- **Release tooling**: normalize version strings for index checks and test installs (e.g., 26.01rc2 -> 26.1rc2).
- **Release tooling**: retry test install when the new version is not indexed yet.
- **Release tooling**: link to the version-specific project page by default.
- **Release tooling**: add `--set-version` to bump VERSION/pyproject, commit, tag, and push.
- **Versioning**: bump VERSION/pyproject to 26.01rc2.
- **Red anchor & scan tooling**: optimize hue offsets and anchor selection; scan all offsets and choose reddest at max chroma; adjust red scoring (|G-B|/(G+B) + (G+B)/(2R)); add multi-stage best-red search, cache seeding/updates; add --best-red + red-scan HTML (coarse/fine/micro), bundle all modes, 0.2 micro step; switch CLI to argparse/named args and remove --scan-mode; treat red offsets as global per mode.
- **YAML-driven config**: add `wheel_specs.yaml` and load defaults in `wheel_specs.py`; load modes/offsets from YAML across tools; simplify YAML to per-mode `target_j`/`red_offset`; add pytest coverage for YAML mode order and offsets; enforce XOR between `shared_m_quantile` and `target_ucs_r`.
- **YAML-driven config**: remove hardcoded mode names from tests and HTML defaults; use YAML mode order everywhere.
- **Versioning**: sync `pyproject.toml` and root `VERSION` to 26.01rc1.
- **Debug & inspection tooling**: label legacy red distance output with the actual YAML mode names used.
- **HTML output**: prefer `dark`/`light`/`xlight` modes by name (when present) for the legacy-style color table columns.
- **HTML output**: require `dark`/`light`/`xlight` in YAML for the legacy table; error if missing.
- **Color name matching & deps**: add `rgb_color_name_match` using seaborn xkcd; add `seaborn` dependency; remove `webcolors`; remove `rcp-color-utils.py`.
- **Testing & engine work**: move module-level asserts into pytest; expand pytest coverage for writers/manifest/helpers/round-trips/validators/xml formatter/yaml tools/string helpers/color wheel; add round-trip coverage across BBQ/text2qti/okla_chrst_bqgen; add QTI ZIP/manifest tests and error-path coverage; fix engine selection ambiguity, item bank merge type tracking, BBQ NUM zero-division handling; update TODO/ROADMAP, mark Canvas QTI 1.2 ORDER as won't implement, expand ROADMAP priorities, and preserve legacy TODO/ROADMAP content.

## 2025-12-29

### Additions and New Features
- Add [docs/TEST_PLAN.md](TEST_PLAN.md) with pytest suite ideas before implementation.
- Add pytest unit and integration coverage for item types, validators, engines, and CLI.
- Add pytest fixtures in `tests/conftest.py` for shared sample items and temp cwd.
- Add integration output checks for QTI ZIPs, human readable, BBQ, and HTML outputs.
- Add pytest unit coverage for text2qti and okla_chrst_bqgen reader parsing.
- Add reader/writer roundtrip smoke tests for BBQ, text2qti, and okla_chrst_bqgen engines.
- Add edge-case tests for text2qti and BBQ reader error paths plus okla unknown-block handling.
- Add unit coverage for missing NUM tolerances in BBQ/text2qti readers.
- Add unit coverage for NUM writers with zero tolerance.
- Add unit coverage for engine registry, manifest generation, YAML helpers, and anti-cheat.
- Add [docs/ENGINE_AUTHORING.md](ENGINE_AUTHORING.md) with engine authoring guidance.
- Add internal engine cleanup notes in `qti_package_maker/engines/ENGINE_CLEANUP.txt`.
- Add docs consistency check to keep engine names in sync with the registry.
- Add unit coverage for BaseEngine filename helpers and histogram output.
- Add CLI error-path coverage for invalid BBQ filenames.
- Add manifest schema metadata checks for QTI v1.2 and v2.1 outputs.
- Add engine class contract smoke tests (imports and write_item wiring).
- Add ZIP safety checks to prevent absolute or parent directory paths.
- Add BBQ parsing error-path coverage for missing correct flags.
- Add BaseItem repr smoke test.

### Behavior or Interface Changes
- Convert script-based tests into pytest functions using fixtures and tmp paths.
- Register pytest `smoke` marker and fix item type test inputs.
- Add format_html_lxml and anti-cheat edge case tests.
- Adjust BaseEngine test harness and anti-cheat expectations for current behavior.
- Use ItemBank.add_item_cls for okla_chrst_bqgen reader to preserve question text.
- Default BBQ NUM tolerance to 0.0 with a warning when the field is missing.
- Fix text2qti MA detection for `[ ]` choices and raise clearer errors for missing NUM/FIB answers.
- Emit explicit tolerance in text2qti NUM writer output (including 0.0).
- Limit BBQ and text2qti read skipping to parse-time ValueError/IndexError.
- Refine engine authoring guidance with overview, discovery command, and ZIP tip.
- Expand engine authoring guidance with examples, mapping table, and troubleshooting.
- Add engine authoring tables for interfaces, artifacts, tests, and failure modes.
- Align engine authoring examples with EngineClass patterns and testing guidance.
- Clarify recommended pytest targets and what they cover for engine authors.
- Rewrite engine docstrings for accuracy and consistency across engine modules.
- Note MkDocs Material light/dark theming for html_selftest in TODO and roadmap.
- Reference MkDocs Material palette tokens in html_selftest theming docs.
- Record engine cleanup completion notes for randomness helper and allow_mixed plumbing.
- Rename random item helper in BaseEngine and update tests.
- Add scoped html_selftest theme injection and palette-aware colors for matching/ordering.
- Document CRC-suffixed JavaScript function naming in html_selftest helpers.
- Use html_selftest theme variables for dropzone borders and reset colors.
- Mark html_selftest MkDocs palette theming as done in TODO/ROADMAP.
- Add html_selftest output validation tests for HTML parsing and theme markers.
- Add html_selftest HTML validator that tolerates JavaScript blocks.
- Update engine docs for html_selftest FIB support and remove stale TODO entry.

## 2025-12-20

### Additions and New Features
- Add `docs/DEVELOPMENT.md` with setup, testing, and engine guidance.
- Add `docs/FORMATS.md` with input/output format notes and engine list.
- Add `docs/TROUBLESHOOTING.md` with common issues and fixes.
- Add `docs/INSTALL.md`, `docs/USAGE.md`, `docs/QUESTION_TYPES.md`, and
  `docs/ENGINES.md` to split README content into focused guides.
- Add `docs/RELATED_PROJECTS.md` and `docs/COMMUNITY.md` to move link lists and
  support info out of README.
- Add `TODO.md` to track feature ideas and missing item implementations, migrated from
  `TODO.txt`.
- Add `ROADMAP.md` to capture longer-form plans such as hints support.
- Add feedback planning section to `ROADMAP.md`.

### Behavior or Interface Changes
- Update `README.md` with documentation links and a backlog pointer.
- Update `TODO.md` to point hint planning at `ROADMAP.md`.
- Move documentation files (changelog, roadmap, todo, style guides, and legacy docs)
  into `docs/` to reduce root-level clutter.
- Split `README.md` into shorter sections with links to new docs.
- Rename `docs/INSTALLATION.md` to `docs/INSTALL.md` and
  `docs/DEVELOPER.md` to `docs/DEVELOPMENT.md`.

### Removals and Deprecations
- Remove legacy `docs/TODO.txt` and `docs/old_README.md` in favor of updated docs.

## 2025-12-12

### Additions and New Features
- Add `qti_package_maker/common/tabulate_compat.py` with a fallback plain-text table renderer.
- Add HTML `<table>` to plain-text conversion in `qti_package_maker/common/string_functions.py`.

### Behavior or Interface Changes
- Use `tabulate_compat` in `qti_package_maker/assessment_items/item_bank.py` and
  `qti_package_maker/engines/engine_registration.py`.
- Pass `allow_mixed` through `qti_package_maker/package_interface.py` when supported, and
  forward it in `qti_package_maker/engines/text2qti/engine_class.py` and
  `qti_package_maker/engines/bbq_text_upload/engine_class.py`.
- Allow table markup in `qti_package_maker/engines/human_readable/write_item.py` content checks.

### Removals and Deprecations
- Remove unused variables in `qti_package_maker/engines/text2qti/write_item.py`.
- Remove unnecessary `global` declarations in `qti_package_maker/common/franken_bptools.py`.

### Fixes and Maintenance
- Ignore `pyflakes.txt` in `.gitignore`.
- Mark tests executable: `tests/test_bbq_converter_all_types.py` and
  `tests/test_human_readable_tables.py`.
