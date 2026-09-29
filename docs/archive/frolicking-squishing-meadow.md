# Port peptidyle's keyboard-first ORDER and MATCH controls into html_selftest

## Context

The user thinks peptidyle-learning-engine improved on qti-package-maker's selftest, especially
for drag-and-drop types. I compared both.

Peptidyle did not copy the selftest code. It rebuilt the controls in SolidJS against its own
no-mouse accessibility contract (`docs/NO_MOUSE_ACCESSIBILITY_CONTRACT.md`). Grading happens on
the server and is all-or-nothing, so peptidyle has no in-browser grading or per-item marks.
Selftest's in-browser grading with per-row marks stays. Peptidyle's interaction model is the part
worth porting.

Comparison (selftest today vs peptidyle):

| Aspect | html_selftest now | peptidyle |
| --- | --- | --- |
| ORDER input | Drag a choice into a table of numbered dropzones; the choice is copied, not moved | One list with Up/Down buttons per row; ArrowUp/Down on those buttons |
| MATCH input | Drag a choice into a dropzone cell only | Click/tap a bank card, then click/tap a prompt slot; drag is optional |
| Keyboard / touch | None; native HTML5 drag only, which does not work on mobile | Full Tab/Space path; tap path; 44px targets |
| Screen reader | None | Polite live region announces each move or assignment; aria-labels on the buttons |
| Duplicates | One choice can fill several zones; a zone cannot be emptied except by Reset | A used choice is disabled or shows "Used in N"; each slot has a Clear button |
| Progress | None until Check | "N of M prompts matched" |
| Drag correctness | No `setData`, drop has no `preventDefault` (can fail in Firefox) | `setData` + `preventDefault`; drops accepted only from the item's own bank |
| Layout | Fixed tables | Responsive columns that stack on narrow screens |
| Grading / marks | Client-side, marks each row right or wrong, partial score | Server-side, all-or-nothing, no per-item marks |
| Shuffle | Shuffled | Not shuffled; possible bug: ORDER may be shown already solved |

Verdict: port the keyboard and click/tap model and drop drag and drop entirely (user decision). Keep selftest's shuffle, client-side
check, per-row marks, and result strings.

## Hard constraints (bp-website contract)

`tests/unit/test_html_selftest_contract.py` locks these, and they must not change:
- the IDs `question_html_<crc>` and `result_<crc>`
- the global function `checkAnswer_<crc>()`, found through the Check button's `onclick`
- the result strings `Correct positions: X of Y` (ORDER) and `Total Score: X out of Y` (MATCH)

Also:
- scope all DOM queries to the item container, as `test_html_selftest_output.py` expects
- keep the output ASCII-escaped, with no trailing whitespace
- keep functions tab-indented and typed
- keep JS as Python strings, following the existing `generate_*_js` pattern

## Design

### ORDER (`qti_package_maker/engines/html_selftest/add_ORDER.py`)
- Replace the dropzone table and choice bank with one shuffled `<ol class="qti-order-list">`.
  - Each `<li class="qti-order-row qti-choice-N" data-value="<token>">` holds four parts:
    - a feedback cell
    - a position number
    - the choice text
    - "Move up" and "Move down" buttons (`.qti-order-move`, `type="button"`, aria-label
      "Move item N earlier/later")
  - Up is disabled on the first row and Down on the last.
- Moving a row relocates the `<li>` in the DOM, renumbers the rows, updates which buttons are
  disabled, and keeps focus on the same button of the moved row. ArrowUp/ArrowDown on a focused
  move button moves the row the same way.
- Add a visually hidden `role="status" aria-live="polite"` region per item: "<text> moved to
  position N."
- No drag and drop. Remove every `draggable` attribute and every `drag*`/`drop` handler.
- Check compares each row's `data-value` with its current position, marks each row with the
  existing check/cross feedback, and writes `Correct positions: X of Y`.
- Grading tokens: keep the `crc_NNN` tokens, compared by DOM order.

### MATCH (`qti_package_maker/engines/html_selftest/add_MATCH.py`)
- Two-column responsive layout: the prompt slots and a choice bank.
  - The choice bank is `<ul id="choiceList_<crc>">`, fixing the current ID collision when several
    items share a page.
  - The bank is shuffled, and distractors are kept.
- Primary path:
  - Click or tap a bank choice button (`aria-pressed`, `.qti-selected`), then click or tap a prompt
    slot button to assign it.
  - Each slot has a Clear button that returns focus to the slot.
  - A used choice is disabled (`.qti-unavailable`), because every correct answer is unique.
  - Assigning into a filled slot frees the old choice.
- No drag and drop. Every control is a native `<button type="button">`, so Tab plus Space/Enter
  work with no extra code. Escape clears the pending selection.
- Show a progress line, "N of M prompts matched", and a polite live region that announces
  "Assigned X to prompt N", "Cleared prompt N", or "Select a choice first."
- Check keeps the per-row marks and `Total Score: X out of Y` (set with `textContent`).

### Shared
- `javascript_functions.py`: rewrite `resetGame_<crc>` so it fully restores the initial state:
  - ORDER: restore the original shuffled order and clear the marks
  - MATCH: clear every slot, re-enable choices, clear the selection, progress and marks
  - both: re-enable Check
  - Implement it by snapshotting the initial `innerHTML` of the interactive region, or by
    rebuilding it from stored data. Pick whichever is shorter.
- `html_functions.py` theme CSS: add the new classes:
  - `.qti-order-*`, `.qti-match-*`, `.qti-selected`, `.qti-unavailable`
  - `.qti-sr-only` (visually hidden)
  - 44px minimum targets, focus-visible outlines, and a stacking media query
  - light, dark and MkDocs variants that reuse the existing variables
- Remove the now-dead drag code, the `.qti-dropzone*` CSS, and the "Drop Your Choice Here"
  placeholders.

## Files

- `qti_package_maker/engines/html_selftest/add_ORDER.py`: rewrite the HTML and JS
- `qti_package_maker/engines/html_selftest/add_MATCH.py`: rewrite the HTML and JS
- `qti_package_maker/engines/html_selftest/javascript_functions.py`: reset
- `qti_package_maker/engines/html_selftest/html_functions.py`: CSS (451 lines; stay under the
  1000-line limit)
- `tests/unit/test_html_selftest_output.py`: update the ORDER/MATCH structure asserts, which
  currently expect dropzone classes. Add one test that every move and assign button has
  `type="button"` and an aria-label, and that each item has a live region.
- `docs/CHANGELOG.md`: add a 2026-09-29 entry
- `docs/ENGINES.md`: update the selftest ORDER/MATCH interaction description
- `README.md` screenshots may go stale; note it and do not regenerate them.

## Verification

1. `source source_me.sh && pytest tests/`: the contract, output, encoding, and lint tests stay
   green.
2. Generate sample pages with `tools/bbq_converter.py -s` from an ORDER and a MATCH bank, writing
   to `output_smoke/`.
3. One-time Playwright check in `tests/_temp/` on the generated HTML (Chromium, plus WebKit mobile
   emulation). It passes if:
   - using only the keyboard (Tab/Space/Arrow) produces a correct answer and `Correct positions:
     N of N` / `Total Score: N out of N`
   - the tap path (click the choice, then the slot) works under touch emulation
   - the generated HTML contains no `draggable` attribute and no `drag`/`drop` listeners
   - Reset restores the initial state
   - two items on one page do not interfere
   - no console errors
   Delete the check afterward per `docs/PYTEST_STYLE.md`.
4. Screenshot one light-mode and one dark-mode render for a visual check.

## Out of scope / notes

- Answer tokens stay readable in the DOM (this is a practice tool; client-side grading already
  exposes answers).
- Tell the user about the peptidyle finding: native ORDER questions appear not to be shuffled, so
  they may be shown already solved. It is a separate repo, so report it but do not fix it here.
