# Blackboard Ultra QTI 2.1 empirical contract

## Status: PARTIAL - table findings under revision

The first round-trip probe (2026-04-14, `output/ultra_probe.zip`) led to
a wrong conclusion about tables. This document is being rewritten as a
second table-only probe runs. Rules below marked **[RETRACTED]** should
not be used to design the engine yet.

What is currently confirmed:

- `<pre>` whitespace is destroyed (still true).
- `&#xa0;` runs and `<br/>` survive (still true).
- CSS is fully stripped (still true).
- `<img>` is structurally broken on export (still true).
- `<hr/>`, `<blockquote>`, `<kbd>` are stripped (still true).
- `<h3>` -> `<h4>` shift (still true).
- `<b>`/`<i>`/`<u>` rewrites (still true).

What is under revision:

- Whether tables render as a grid. The hand-built Ultra question
  (`ULTRA/manually-created-ultra-question/`) and its round-trip
  (`ULTRA/Manual-Roundtrip-Screenshot_2026-04-14_at_12.04.49_PM.png`)
  both show a real 2-column grid. My earlier "tables collapse" claim
  was based on the Michaelis-Menten render - that collapse has a
  different root cause, not a blanket Ultra limitation.
- Which exact `<th>`/`<td>` cell shape triggers grid rendering vs.
  stacked rendering. New probe `output/ultra_table_probe.zip` tests
  12 structural variants to isolate this.
- Whether `<pre>`/`&nbsp;`/`<br/>` was ever needed at all. Probably
  not - tables are the primary solution.

See [output/ultra_table_probe.zip](../output/ultra_table_probe.zip) and
[tools/build_ultra_table_probe.py](../tools/build_ultra_table_probe.py).
The section "Locked engine decisions" below is **[RETRACTED]** until
the second probe lands.

---


Empirical contract for what Blackboard Ultra accepts, rewrites, or destroys on
QTI 2.1 import followed by re-export. This document is the single source of
truth for the `blackboard_qti_v2_1_ultra` engine's HTML sanitizer and layout
renderer. Do not change it without a fresh round trip.

## Source of findings

One manual round trip on 2026-04-14:

- Source ZIP: [output/ultra_probe.zip](../output/ultra_probe.zip),
  built by [tools/build_ultra_probe.py](../tools/build_ultra_probe.py).
- Re-export after import/export through an Ultra sandbox:
  [ULTRA/ultra_probe-roundtrip/](../ULTRA/ultra_probe-roundtrip/).
- 15 small MC items, one probe dimension each. All 15 imported and
  re-exported as well-formed XML.

Baseline evidence from an earlier round trip:

- Original Learn-shaped package:
  [ULTRA/blackboard_qti_v2_1-michaelis_menten_table-Km/](../ULTRA/blackboard_qti_v2_1-michaelis_menten_table-Km/)
- Ultra re-export of that same package:
  [ULTRA/ExportFile_ultra_sandbox_nvoss/](../ULTRA/ExportFile_ultra_sandbox_nvoss/)
- Hand-built Ultra-native question:
  [ULTRA/manually-created-ultra-question/](../ULTRA/manually-created-ultra-question/)

## The single rendering primitive

Lock this at the top of the document so no future reader can miss it.

```
&nbsp; + <br/> is the only reliable layout system in Ultra QTI.
```

Everything else (`<pre>`, `<table>`, CSS, inline styles, deprecated
presentational attributes) either collapses, gets stripped, or is structurally
unreliable. All engine layout decisions flow from that one sentence.

## Allowed tags (confirmed surviving re-export)

Tag-level survival only. Whether a surviving tag actually **renders** as
expected is tracked separately below under "Render correctness vs round-trip
stability".

| Tag | Round-trip | Notes |
| --- | --- | --- |
| `p` | YES | Primary container. Wrap all text content in `<p>`. |
| `span` | YES | Attribute-free. Also used as the replacement for `<u>`. |
| `br` | YES | Use `<br/>` for vertical spacing. Runs survive (`<br/><br/>` OK). |
| `div` | YES | Preserved with contents. Ultra wraps the itemBody in an outer `<div><div>...</div></div>` on export; match the pattern on emit. |
| `sub` | YES | Survives byte-for-byte. |
| `sup` | YES | Survives byte-for-byte. |
| `em` | YES | Also the destination Ultra rewrites `<i>` to. |
| `strong` | YES | Also the destination Ultra rewrites `<b>` to. |
| `code` | YES | Survives. |
| `ul` | YES | Survives including nesting. |
| `ol` | YES | Survives including nesting. |
| `li` | YES | Survives. |
| `table` | YES (structurally) | **Layout unreliable** - see below. |
| `tbody` | YES | Required wrapper inside every `<table>`. |
| `tr` | YES | |
| `th` | YES | Cell content must be wrapped in `<p>`. |
| `td` | YES | Cell content must be wrapped in `<p>`. |
| `h4` | YES | **But** `<h3>` is shifted to `<h4>` on import. |
| `h5` | YES | **But** `<h4>` is shifted to `<h5>` on import. |
| `pre` | Tag yes, semantics no | Whitespace destroyed. Use as plain `<p>`, or avoid. |

## Rewritten or stripped

| Input | What Ultra does | Use instead |
| --- | --- | --- |
| `<b>` | Rewrites to `<strong>` | Emit `<strong>` directly |
| `<i>` | Rewrites to `<em>` | Emit `<em>` directly |
| `<u>` | Rewrites to `<span>` (no styling, underline is lost) | Do not use `<u>` |
| `<kbd>` | Stripped entirely, content preserved | Emit plain text or wrap in `<code>` |
| `<hr/>` | Stripped entirely | Do not use |
| `<blockquote>` | Stripped (children preserved) | Do not use |
| `<h3>` | Renumbered to `<h4>` | Emit `<h4>` directly |
| `<h4>` | Renumbered to `<h5>` | Emit `<h5>` directly |
| `<h1>`, `<h2>` | Not probed | Avoid; the h-shift pattern suggests Ultra reserves these for its own UI |
| `<style>` element | Stripped | Do not emit under any circumstances |
| `<img src="csfiles/...">` | **Severely broken** - see below | Do not emit `<img>` |
| `class` attribute | Stripped everywhere | Do not emit |
| `style` attribute | Stripped everywhere | Do not emit |
| `border`, `cellpadding`, `cellspacing`, `align`, `width`, `height`, `bgcolor`, `face`, `color` | Stripped everywhere | Do not emit |

## The `<img>` disaster

Probe item 15 (`img_minimal`) demonstrates that `<img>` is broken beyond use on
Ultra's re-export path. Source was:

```xml
<img src="csfiles/home_dir/probe_tiny.png" alt="tiny probe image"
     width="32" height="32"/>
<p>Fallback text (always visible):</p>
<pre>[tiny image would appear here]</pre>
```

Ultra re-exported as:

```xml
<img src="@X@EmbeddedFile.requestUrlStub@X@/bbcswebdavnull" alt="tiny probe image">
 <p>Fallback text (always visible):</p>
 <pre>[tiny image would appear here]</pre>
</img>
```

Four separate failures in one block:

1. Our `csfiles/home_dir/probe_tiny.png` was not tracked by Ultra as a managed
   asset. Ultra replaced the `src` with a null-file stub placeholder
   (`@X@EmbeddedFile.requestUrlStub@X@/bbcswebdavnull`) and dropped the PNG -
   `csfiles/home_dir/` in the re-export is empty.
2. `width`/`height` dropped.
3. The self-closing `<img/>` became a container tag `<img>...</img>`, and
   every following sibling (our fallback `<p>` and `<pre>`) was absorbed as a
   child of the unclosed img. The output is well-formed XML but
   structurally nonsense.
4. Rendering in Ultra is therefore undefined and we must treat `<img>` as
   completely unavailable through the QTI import path.

**Engine policy:** the Ultra sanitizer strips `<img>` unconditionally. PNG
rendering is dead. There is no known way to reference a local asset from a
third-party QTI import.

## Whitespace behavior

This is the finding that kills `<pre>` as a layout strategy.

| Construct | Result |
| --- | --- |
| Runs of regular spaces inside `<p>` | Collapsed to a single space |
| Leading/trailing spaces inside `<p>` | Stripped |
| Tab characters (`\t`) anywhere | Converted to single spaces, then collapsed |
| Newlines inside `<pre>` | **Collapsed to single spaces** |
| Runs of regular spaces inside `<pre>` | **Collapsed to a single space** |
| `<pre>` tag itself | Preserved as a tag, but whitespace inside is normalized like any other text node |
| `&#160;` (non-breaking space) | Preserved byte-for-byte inside `<p>`, `<pre>`, `<span>`, and `<td>` |
| Runs of `&#160;` (5+) | Preserved byte-for-byte |
| `<br/>` | Preserved |
| Runs of `<br/><br/>` (up to 5 consecutive observed) | Preserved |

Confirmed from probe items 1 (pre_alignment), 2 (pre_vs_p), 3 (nbsp_columns),
7 (whitespace_stress). Item 1's `<pre>` went from 15 newlines to zero; item 7
shows `\t` becoming spaces and collapsing; items 3 and 4 show nbsp runs of 5
surviving.

**Therefore**: `<pre>` is functionally equivalent to `<p>` in Ultra. Do not
rely on `<pre>` for alignment. Do not emit `<pre>`; normalize to `<p>`.

## Entity behavior

| Input | Re-exported as |
| --- | --- |
| `&lt;`, `&gt;`, `&amp;` | Preserved as `&lt;`, `&gt;`, `&amp;` |
| `&quot;`, `&apos;` | Converted to literal `"`, `'` |
| `&#945;` (decimal numeric) | Converted to literal Unicode (`&#945;` is alpha) |
| `&#x03B1;` (hex numeric) | Converted to literal Unicode |
| `&#160;` (nbsp) | Preserved as `&#xa0;` (hex numeric form, kept) |

The engine may emit either numeric form for most characters - Ultra will
normalize them to literal Unicode on re-export, which is fine as long as the
output file is UTF-8. Nbsp stays numeric because it has no non-ambiguous
literal representation.

## Structural facts (QTI shell, not itemBody)

These match what we already saw in the hand-built Ultra sample and are now
re-confirmed for a fresh import-then-export cycle:

- Manifest shape from `manually-created-ultra-question/imsmanifest.xml` is
  accepted verbatim. Our probe manifest came through unchanged modulo
  insignificant whitespace reformatting.
- Test file shape `qti21/question_bank00001.xml` is accepted. Ultra
  renames our `assessmentSection/@title` to "Section 1" but keeps
  everything else.
- Ultra rewrites every item's `@identifier` to `QUE__<N>_1` style. Our
  original identifiers do not survive; pick any stable pattern and let
  Ultra rename.
- Ultra wraps each `itemBody` content block in an outer `<div><div>...</div></div>`
  on export. Our engine should emit this pattern on the way in so that
  source and re-export match.
- Ultra wraps each `simpleChoice` body in `<div><p>...</p></div>`. Emit
  the same pattern.
- `responseDeclaration cardinality="multiple"` even for MC. Unpadded
  `answer_N` identifiers that match `simpleChoice/@identifier` exactly.
- `outcomeDeclaration` triple: `SCORE` (float default 0), `FEEDBACKBASIC`
  (identifier), `MAXSCORE` (float default 0). Already produced by
  `blackboard_qti_v2_1.item_xml_helpers.create_outcome_declarations_big`.
- `responseProcessing` with a full `<responseIf>` setting `SCORE` from
  `MAXSCORE` and `FEEDBACKBASIC` to `correct_fb`, plus a `<responseElse>`
  setting `FEEDBACKBASIC` to `incorrect_fb`.
- `choiceInteraction shuffle="false"`.

## Render correctness vs round-trip stability

The plan asks to track these as separate columns. Here are the answers.

| Probe | Round-trip stable? | Render correctly? | Notes |
| --- | --- | --- | --- |
| 1 `pre_alignment` | Tag yes, content no | NO | Newlines collapsed, monospace unknown but moot |
| 2 `pre_vs_p` | Tag yes, content no | NO | `<pre>` whitespace destroyed equally with `<p>` |
| 3 `nbsp_columns` | YES | **Expected YES** | Need visual confirmation from screenshot, but content is intact |
| 4 `hybrid_nbsp_br` | YES | **Expected YES** | Same |
| 5 `table_baseline` | YES | NO (per Michaelis-Menten baseline) | Table tags survive; Ultra renders them as a single-column vertical stack |
| 6 `table_cell_shapes` | YES | NO | Same as 5 |
| 7 `whitespace_stress` | No - Ultra collapses runs | NO | Tabs and space runs lost |
| 8 `table_inline_attrs` | Attributes stripped | NO | All presentational attrs removed |
| 9 `inline_formatting` | Partial (see rewrites table) | YES for sub/sup/em/strong/code | `<u>` and `<kbd>` lost |
| 10 `div_vs_p` | YES | YES | Both survive |
| 11 `entities` | YES (after normalization) | YES | Numeric refs become literal Unicode |
| 12 `lists` | YES | YES | Including nested |
| 13 `headings_hr` | Headings shift, hr/blockquote stripped | Partial | Use `<h4>`/`<h5>` directly |
| 14 `css_inline_and_style_tag` | NO (all CSS stripped) | NO | All variants lose styling |
| 15 `img_minimal` | **BROKEN** | NO | Structurally corrupted on export, PNG dropped |

A construct that is round-trip stable but does not render correctly is still
useless for layout. `<table>` falls into this bucket: it survives re-export
unchanged but renders as a vertical stack. Do not use it for layout.

## Locked engine decisions

### Table strategy

**`<p>` with `&#xa0;` padding and `<br/>` row separators.** There is no
fallback ladder; the other rungs are empirically dead.

```xml
<p>
[S]&#xa0;&#xa0;&#xa0;&#xa0;V0<br/>
0.0001&#xa0;&#xa0;20.0<br/>
0.0002&#xa0;&#xa0;26.7<br/>
...
</p>
```

Implementation rules for the layout renderer:

1. No regular spaces for alignment. Ultra collapses every run of normal
   spaces, including inside `<pre>`. Use `&#xa0;` exclusively for horizontal
   padding.
2. Column gap is a fixed run of `&#xa0;` (suggest 2-4 nbsps between
   columns). Tune during implementation.
3. Row break is `<br/>`. Do not use one `<p>` per row - that introduces
   Ultra's default inter-paragraph vertical gap which makes numeric tables
   unreadable.
4. Right-align numbers by left-padding each cell with `&#xa0;` up to the
   column width.
5. Multi-line headers use `<br/>` within a single header cell (rendered
   as the first row of the nbsp table, not as an HTML header).
6. Do not emit `<table>` for layout. `<table>` is allowed through the
   sanitizer only to keep probe item 5 well-formed; the engine never
   generates one from user input.

### Sanitizer rules (final)

- Allowed tags (strict allowlist):
  `p`, `span`, `br`, `div`, `sub`, `sup`, `em`, `strong`, `code`,
  `ul`, `ol`, `li`, `h4`, `h5`, `table`, `tbody`, `tr`, `th`, `td`.
- Tag rewrites:
  - `<b>` -> `<strong>`
  - `<i>` -> `<em>`
  - `<u>` -> `<span>`
  - `<h1>`, `<h2>`, `<h3>` -> `<h4>` (match Ultra's own downshift)
  - `<h4>` -> `<h5>`
  - `<pre>` -> `<p>`
- Tag strips (content preserved, wrapper removed):
  `<kbd>`, `<hr>`, `<blockquote>`.
- Tag strips (content also dropped):
  `<img>`, `<style>`, `<script>`, any other `<h>` level not listed, any
  other tag not in the allowlist above.
- Attribute strips (unconditional everywhere):
  `style`, `class`, `border`, `cellpadding`, `cellspacing`, `align`,
  `width`, `height`, `bgcolor`, `face`, `color`, `id` (Ultra rewrites),
  plus any legacy presentational attribute.
- Whitespace normalization:
  - Do not emit literal tab characters.
  - Collapse runs of regular spaces to a single space (matches what Ultra
    does anyway, eliminates surprise).
  - Strip leading and trailing whitespace from text nodes.
- Span hygiene:
  - Collapse empty nested `<span>` wrappers (observed ghosts in the
    hand-built sample at `manually-created-ultra-question/qti21/assessmentItem00001.xml:6`).
  - Drop `<span>` wrappers that have no attributes and only text content.
- Cell content shape:
  - Every `<td>`/`<th>` child wraps its direct text in `<p>`.
- Post-sanitize reparse check: round-trip the sanitized tree through
  `lxml.html.fromstring(...).tostring(...)` and raise if the tree
  structure changes or the output fails to parse.

### What the table_render stage does

Replaces the plan's three-rung ladder with a single `render_table()` entry
point:

- Parses the input HTML table with `lxml.html`.
- For each row, pulls the text content of each cell (sanitized with the
  rules above, but with internal markup like `<sub>` preserved).
- Computes column widths from the maximum string-length of each column
  (counting nbsp runs as one character each for visual alignment purposes;
  rendered characters for everything else).
- Emits a single `<p>` containing rows separated by `<br/>`, cells
  right-padded (or left-padded for text cells) with `&#xa0;` runs, and
  column gaps of `&#xa0;&#xa0;&#xa0;` (tune).

No `<pre>` path. No `<table>` path. No `<img>` path. One strategy.

## What this means for the plan

These plan items are obsolete or changed:

- Phase 5 ladder ordering (`<pre>` first, then `&nbsp;`, then bare
  `<table>`): **replaced** with a single nbsp-only strategy. The
  `<pre>` rung is deleted.
- `table_render.py` unit tests for three rungs: **replaced** with tests
  for one rung.
- Sanitizer `<div> -> <p>` normalization: **reverted**. Ultra preserves
  `<div>` unchanged, so keep `<div>` on the allowlist and do not rewrite.
- Sanitizer allowlist `<pre>`: **removed**. Rewrite `<pre>` to `<p>`
  during sanitization.
- Sanitizer `<img>` allowlist entry: **removed**. Strip unconditionally.
- Sanitizer heading handling: **add** the h-shift rule (`h3 -> h4`,
  `h4 -> h5`).

## Next

Proceed to M3 (type_normalize) and M4 (html_sanitize) and M5 (table_render
as a single nbsp strategy) in parallel. All three are now unblocked.
