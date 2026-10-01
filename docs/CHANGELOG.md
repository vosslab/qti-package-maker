# Changelog

## 2026-09-30

### Additions and New Features

- Added a content-keyed in-memory PNG cache shared by items and all three ZIP
  packaging engines within one `QTIPackageInterface`. Direct callers may pass
  `html_to_image_cache` to engines or `cache` to `convert_bank`.

### Behavior or Interface Changes

- MATCH self-tests use content-sized tables with bounded answer and prompt columns, cell-filling
  slots, and landscape feedback marks. Narrow layouts follow the embedded question's width.
  CSS ellipsis replaces the arbitrary 30-character cutoff while preserving full accessible text.
- With a MATCH slot focused, a displayed letter moves that choice from its other rows and
  announces the changes. Dragging and clicking allow duplicate guesses; all choices stay available.
- MATCH and ORDER group larger Check Answer and Reset buttons with the score directly below
  the answer area. All self-test types, including MC and MA, share readable 44px-high action
  buttons and remain checkable after correct answers. Pressing a button shrinks it slightly
  without shifting layout; reduced-motion mode uses shading without movement.
- Chromium starts only for an uncached table or MathML render and reuses one page
  with bundled fonts loaded once. Canvas-only and fully cached conversions start no browser.
- Shipped selectors parse each field once; canvases are drawn and embedded before
  outermost tables are captured on the same tree. Image names, alt text, nested-table
  selection, source banks, and engine-owned media cleanup stay unchanged. Custom
  string finder callbacks retain their fragment and empty-selection behavior.

### Fixes and Maintenance

- Rich MATCH prompts use the available column width instead of the 36-character prose limit.
  Pedigrees and other diagrams remain full size and scroll only when the question container
  is too narrow; ordinary text prompts retain their compact width. Chromium desktop, narrow,
  drag/drop, keyboard, touch, and grading checks passed; full pytest suite: 3,834 passed.
- Fixed self-test HTML exports retaining trailing spaces and tabs in authored
  CRLF or bare-CR lines. Output now normalizes those endings to LF before stripping
  trailing whitespace; stored question content stays unchanged.
- Fixed trailing HTML layout padding in `make_question_pretty`, where tag conversion
  produced plain-text lines with spaces before breaks. Plain-text conversion now
  constructs clean LF lines, including decoded entities and rendered tables.
- Six-pass code audit: clarified that the shared cache lasts for the interface's lifetime,
  aligned the archived objective with that boundary, and removed test assertions on exact
  serialization attributes and cache counters while retaining behavior checks.
- Audit follow-up: cache entries include renderer identity, so changing custom callbacks
  on an interface or explicit cache produces the requested images. Default table sessions
  continue sharing PNGs across all three engines. The cache retains callback identities.
- Extended the existing shared-cache packaging contract to Blackboard export, including
  its csfiles image naming, and added the demonstrated renderer-switch regression contract.
- Rotated older day blocks into [CHANGELOG-2026-09a.md](CHANGELOG-2026-09a.md)
  after the active changelog exceeded its 800-line threshold.

### Decisions and Failures

- Native pressed-button styling differed across browsers: Firefox omitted keyboard feedback,
  and WebKit retained a pressed appearance after focus moved mid-keypress. Shared visual press
  state now follows pointer/keyboard release, cancellation, and focus loss while native buttons
  continue handling activation. Pointer focus loss in Safari is released by pointerup/cancel.
- Audit reproduction: changing renderer callbacks on one interface reuses the previous
  renderer's PNG, because keys contain family/content but no renderer configuration.
  The second callback was skipped. Resolved by adding renderer identity to the cache key;
  the red/blue/red regression now verifies correct images and reuse of the first callback.
- Retained page swapping. Three prototype runs on the frozen six-table corpus gave
  median 0.460081 s for swapping versus 0.459025 s for batching. Batching fails
  the 25 percent speed improvement threshold and changes one of six decoded images.
- The cache lifetime follows the approved per-interface design. It is not process-global;
  separately constructed interfaces need an explicitly shared cache to reuse PNGs.
- Deferred the optional WeasyPrint experiment; Chromium remains the renderer.
- The original one-third runtime target is an experiment goal, not a product latency
  requirement. Gate performance on avoiding duplicate renders and unnecessary browser
  launches; retain timings as comparative evidence and profile any measured regression.

### Developer Tests and Notes

- MATCH/ORDER browser coverage now checks letter moves, repeated guesses, independent questions,
  repeated correct checks, full-text ellipsis, cell-filling slots, and bounded layout with long
  text and oversized rich prompts in narrow embedded panels.
- Self-test controls verification: all 3,822 pytest cases pass. Firefox, Chromium, and WebKit
  pass the expanded browser journey, including mouse/Space/Enter feedback, focus-loss cleanup,
  reduced motion, and rechecking all seven question types. Chromium and WebKit also pass touch
  controls. Website-style genetics, protein, and MC/MA previews were visually reviewed at desktop
  and narrow widths; artifacts remain in `output_smoke/match_website_preview/`.
- Audit follow-up verification: all 3,822 pytest cases pass. A fresh real Chromium run
  across all three formats launches one browser, renders six tables and one canvas,
  and produces 18 PNGs byte-identical to the prior verified corpus. Report retained at
  `output_smoke/html_to_image_baseline/audit_fixes/browser_cache_report.json`;
  the temporary verification script was removed.
- Audit cleanup verification: all 3,819 pytest cases pass. A temporary renderer-switch
  reproduction confirms the second renderer is never called and its package contains the
  first renderer's pixels. Removed the probe after recording the finding; no new permanent
  test or cache design change was introduced during the audit.
- Initial three-format corpus: 3.7903 s before versus 0.8854 s after (4.28 times faster),
  Chromium launches 3 to 1, table renders 18 to 6, canvas draws 3 to 1.
  All 18 packaged PNGs have identical dimensions and decoded RGBA pixels;
  packaged image names and src/alt attributes also match. The cache holds 302,332 bytes
  of PNGs with seven misses and 14 hits. Table work excluding launch drops from
  2.7395 s to 0.4314 s; post-change tree work excluding rendering is 0.0059 s.
- Supplemented the numeric sizing/PCR tables with actual `gellib` gel bands and
  agglutination wells, comparing immutable committed renderer/transform sources against
  the current code. This three-format run drops from 1.5107 s to 0.4203 s
  (3.59 times faster), launches 3 to 1 and screenshots 6 to 2. All six additional
  PNGs and logical ZIP contents match, excluding the Blackboard creation-time comment.
- Default conversion parses exactly once per uncached field: 72 field calls include
  54 cache misses and 18 repeated fields; precisely 54 HTML parses occur.
- Actual three-format CLI packages pass integrity checks. All 50 macromolecule questions
  export with real Chromium and pass bptools Blackboard ZIP validation. Visual checks
  confirm a readable data table and the molecule beside its information table.
- Standalone MathML and a table/MathML/table sequence match the committed renderer
  byte for byte and pixel for pixel. Firefox, Chromium, and WebKit pass the self-test
  drag runner, including keyboard, grading, recovery, isolation, and touch alternatives.
- Final clean `source source_me.sh && pytest tests/`: 3,815 passed, including pyflakes,
  function typing, source line limits, engine-option documentation, and Markdown links.
  Removed all temporary probes and archived the completed plan and execution record.

## 2026-09-29

### Behavior or Interface Changes

- MATCH slots return to a fixed 180px width and 44px height (bounded by available width on
  narrow screens). Assigned slots again show truncated plain text, keeping rows compact while full
  formatted choices remain in the bank below. Tooltips and accessible names retain the full
  text; Reset clears the tooltip along with the assignment.
- Self-test retains native drag and drop: drag ORDER rows to reorder them and MATCH bank answers
  into prompt slots. ORDER also has Move up/down buttons and arrow-key shortcuts. MATCH also has
  select-then-assign buttons, one Reset beside Check Answer, and Escape cancellation. Keyboard and touch
  controls supplement dragging. MATCH keeps the prompt table above a wrapping colored choice
  bank; removed the extra progress/status displays, used-choice labels, and per-row Clear buttons.
  MATCH Reset stays visible and resets all assignments, pending selection, and grading using
  the existing reset logic. The label describes the complete reset, including grading.
- Preserved the self-test palettes, bordered matching table, Check/Reset styling, partial scores,
  per-row feedback, and website result strings. Controls stack on narrow screens and announce
  changes through a polite live region. Reset restores the initial order or clears all matches;
  edits clear stale grading marks and re-enable Check.
- README screenshots show the earlier controls and have not been regenerated.
- HTML builders, ORDER/MATCH interaction scripts, and control CSS now live in separate
  modules. A shared item-scoped native drag module handles payloads, target highlighting, and
  cancellation; each interaction reuses its movement or assignment logic for every input path.
  Shared grading/reset helpers preserve the website integration contract.

### Fixes and Maintenance

- HTML-to-image conversion prepares RDKit canvas PNGs before screenshotting
  their enclosing tables. Nested tables remain HTML inside one outermost-table
  screenshot, and intermediate canvas PNGs are omitted from the package.
  This fixes macromolecule exports that failed after table replacement removed
  a still-scheduled canvas.
- Synchronized shared style guides, tests, and repository support files from the starter template.

### Developer Tests and Notes

- Compact MATCH slots pass the existing native drag journey in Firefox, Chromium, and WebKit,
  including unchanged slot dimensions after assignment, full bank text, tooltips, grading,
  keyboard interaction, and Reset. The 60 focused self-test output/contract tests also pass.
- Native drag regression checks pass in Firefox, Chromium, and WebKit using real mouse drags:
  ORDER movement in both directions, MATCH assignment/replacement, partial/full grading,
  Clear, cancellation, Reset, and item isolation. Keyboard paths and Chromium/WebKit touch
  alternatives also pass. The permanent runner is `tests/playwright/playwright_selftest_drag.py`;
  failures require repairing the interaction before accepting a control change. All 3,702
  pytest tests pass after restoring dragging.
- Self-test update: all 3,702 pytest tests pass. Temporary browser walkthroughs pass in
  Firefox, Chromium, and WebKit, including keyboard completion, scoring, reset, and item
  isolation; Chromium/WebKit touch emulation also passes. Light/dark checks at 320-1100px
  and oversized graphical answers pass with no serious or critical axe findings.
- Added one regression test for a canvas inside four nested tables alongside
  a standalone canvas: the table renderer receives an embedded molecule image,
  and the package contains the final table image plus the standalone molecule.
- All 3,661 pytest tests pass. A one-time real Chromium export of all 50 current
  macromolecule questions passes package integrity checks; visual inspection of
  the first question confirms its molecule appears beside the information table.
