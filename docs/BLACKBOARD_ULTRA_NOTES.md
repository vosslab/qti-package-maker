# Blackboard Ultra QTI 2.1 empirical contract

Empirical contract for what Blackboard Ultra accepts, rewrites, or destroys
on QTI 2.1 import/export. Findings are derived from manual round trips
through an Ultra sandbox, not from Anthology's documentation, because
Anthology's docs are silent on almost every question that matters to a
third-party QTI producer.

**Status (2026-07-02): the dedicated `bb_ultra_qti_v2_1` engine described
throughout this document was removed as redundant.** Field evidence showed
every `blackboard_qti_v2_1` export already imports cleanly into Ultra with
only per-feature degradation (matching skipped, table widths/color/most
inline CSS stripped), and the gate D visible-figure probe round confirmed
images render in Ultra from `blackboard_qti_v2_1`-shaped QTI 2.1 and from
`blackboard_export_zip` via "Import from file" (which also carries
matching questions Ultra's QTI 2.1 importer skips). See
[docs/ENGINES.md](ENGINES.md) for the current supported Ultra paths and
`docs/CHANGELOG.md`'s 2026-07-02 entry for the removal rationale. This
document is retained in full as the empirical record of Ultra's HTML,
table, and identifier behavior discovered while that engine was built;
links to the removed engine's source files below are dead and kept as
historical citations only.

Last updated: 2026-04-14 (development history); removal noted 2026-07-02.

## Executive summary (for non-technical readers)

Blackboard Ultra is substantially more restrictive than Blackboard Learn
(Original) for imported assessment items. When a QTI package authored for
Learn is imported into Ultra, Ultra:

- silently drops entire question types it does not support,
- strips every `style=` attribute, every `class=` attribute, and every
  `<style>` CSS block,
- strips every deprecated presentational attribute from tables
  (`border`, `cellpadding`, `cellspacing`, `align`, `width`, `height`,
  `bgcolor`),
- rewrites heading levels downward,
- rewrites or drops several HTML tags,
- does not accept inline images through the documented `<img>` path used
  by Learn,
- does not render SVG,
- does not expose any mechanism to control table column widths.

The practical consequences:

1. **Plain data-table content works.** Michaelis-Menten kinetics, gel
   migration tables, numeric results - any table that is tabular data and
   not hand-drawn graphics - renders correctly in Ultra after a one-line
   HTML fix in the exporter (see "The Michaelis-Menten root cause" below).
2. **Chemistry diagrams drawn with HTML tables do not work.** The
   biochem problem generators that use `<table>` + `colspan` + `rowspan`
   + zero-padding cells to draw Fischer projections, Haworth projections,
   bond lines, and sugar configurations cannot survive Ultra at all.
   There is no CSS route, no column-sizing route, and no styled-cell
   route. The only path forward is pre-rendering the diagram to a PNG
   and embedding it as a managed asset, which is deferred to a follow-up
   project.
3. **`ORDER` (sequence / drag-to-order) questions are silently dropped
   by Ultra's importer.** Anthology's own documentation lists `Ordering`
   as an unsupported type in Common Cartridge imports. The engine
   refuses to emit these, with a warning, so nothing is silently lost.
4. **Hot Spot questions cannot round-trip.** Even though Anthology lists
   Hot Spot as a supported Ultra question type, when an Ultra-authored
   Hot Spot question is re-exported, the export log reports it was
   skipped: "Warning: ... contains 1 questions that could not be
   exported as common cartridge questions. Those questions were
   skipped." Hot Spot is authorable but not round-trip stable.
5. **Styling choices are not portable.** Text color, background color,
   font size, font family, column widths, and text alignment are all
   stripped on export even when the Ultra WYSIWYG editor renders them
   while authoring. Ghost `<span>` wrappers remain where styles used to
   live. If your Learn content depends on colored text or highlighted
   cells for meaning, that meaning is lost on import.
6. **Underline is lost.** `<u>` is rewritten to an empty `<span>`.
   Bold and italic survive as `<strong>` and `<em>`.

The upshot for your old Learn content: prose-heavy questions with
inline formatting, data tables, numeric answers, matching, multiple
choice, multiple answer, fill-in-the-blank, and multi-blank fill-in all
port cleanly. Diagram-heavy questions (carbohydrate chemistry, protein
structures, anything drawn in HTML rather than rendered to an image) do
not port until the image follow-up project lands.

## Field evidence: blackboard_qti_v2_1 exports import into Ultra (2026-07-02)

User-verified field report, 2026-07-02, on real-world `blackboard_qti_v2_1`
exports imported into Ultra (paraphrased closely): every `blackboard_qti_v2_1`
export tried with Ultra works, except for known issues - matching questions
are skipped, table widths are removed, color is removed, and most inline
CSS is removed.

Implications for the engine split:

- The lightweight `blackboard_qti_v2_1` exporter (deliberately minimal,
  required fields only) serves BOTH Learn Classic and Ultra. The format is
  shared; there is no separate Ultra-only wire format for these exports.
- Ultra-side degradations reported here are per-feature and graceful, not
  package rejections. Matching questions are skipped on import; table
  widths, colors, and most inline CSS are stripped. This matches the
  attribute-stripping and tag-survival findings documented below, and
  confirms none of it blocks the rest of the package from importing.
- Matching questions reach Ultra via the `blackboard_export_zip` path
  ("Import from file") instead of `blackboard_qti_v2_1` ("Import from QTI
  2.1 package"), since Ultra's QTI 2.1 importer skips them.
- `bb_ultra_qti_v2_1`'s remaining role is enforcing and normalizing around
  these Ultra limits (sanitizing HTML to the tag/attribute allowlist below,
  refusing unsupported question types with a warning), not producing a
  materially different wire format from `blackboard_qti_v2_1`.

## Source of findings

Three manual round trips through an Ultra sandbox on 2026-04-14:

- **Probe 1 (15 dimensions):**
  `output/ultra_probe.zip`, built by
  `tools/build_ultra_probe.py`. Re-export
  preserved at
  `ULTRA/ultra_probe-roundtrip/`. Each
  item isolates one dimension: `<pre>`, nbsp columns, bare `<table>`,
  cell shape variants, whitespace, inline formatting, div-vs-p,
  entities, lists, headings, CSS, and minimal `<img>`.
- **Probe 2 (12 table variants):**
  `output/ultra_table_probe.zip`, built
  by `tools/build_ultra_table_probe.py`.
  Re-export and 12 rendering screenshots preserved at
  `ULTRA/ultra_table_probe/`. Holds the
  dataset constant (a 2-column kinetics table) and varies only the table
  HTML structure - bare text cells, wrapped cells, with and without
  `<tbody>`, with and without `<th>`, nested spans, legacy attributes,
  and the exact shape the Learn engine emits.
- **Image format probe:**
  `ULTRA/image_test/` - a question hand-built in
  Ultra's editor with an image attachment, then exported. This revealed
  the canonical Ultra-native image embedding pattern and the Hot Spot
  export failure (see below).

Supporting evidence:

- Original Learn-shaped Michaelis-Menten package:
  `ULTRA/blackboard_qti_v2_1-michaelis_menten_table-Km/`
- Ultra re-export of that same package:
  `ULTRA/ExportFile_ultra_sandbox_nvoss/`
- Hand-built Ultra-native question (canonical shape reference):
  `ULTRA/manually-created-ultra-question/`
- Anthology's Ultra question type documentation:
  `ULTRA/question-banks.html`

## The Michaelis-Menten root cause (important)

Earlier analysis concluded that Ultra could not render HTML tables,
based on screenshots showing a Learn-authored Michaelis-Menten kinetics
table collapsing into a vertical stack on first import. That conclusion
was wrong. The real root cause is a single HTML5 parser bug triggered by
one line of the Learn engine's output:

```
<colgroup width="160"/>
```

`<colgroup>` is not a void element in HTML5. The trailing slash is
ignored, and the browser's HTML parser treats the element as an
unclosed open tag. The next sibling `<colgroup width="160"/>` becomes a
child of the first open one, the `<tr>` that follows is parsed in the
wrong insertion mode, and the entire table tree construction breaks.
The renderer falls back to flowing cell text as block content, which
looks like "tables do not work" but is actually "one self-closing tag
broke the parser."

Ultra's own re-export serializer emits paired `<colgroup></colgroup>`
tags, which parses correctly. This is why re-importing Ultra's own
re-export of the same content renders the table as a proper grid on
first try:

- Learn-authored ZIP imported: broken (screenshot:
  `ULTRA/Ultra-Screenshot_2026-04-14_at_10.54.06_AM.png`)
- Ultra re-exported the broken import.
- The re-export was re-imported into Ultra.
- Renders as a proper grid (screenshot:
  `ULTRA/Screenshot_2026-04-14_at_12.43.48_PM.png`)

The content is identical. The only difference is the serialization of
the `<colgroup>` tag. The new `bb_ultra_qti_v2_1` engine avoids the bug
by re-serializing every HTML fragment through `lxml.html.fromstring` +
`lxml.html.tostring`, which repairs self-closing non-void tags
uniformly.

Fixing the Learn engine to match is out of scope; the new engine just
does not emit the broken form.

## Supported question types

From `ULTRA/question-banks.html` (Anthology's official docs for Ultra
question banks), Ultra's Common Cartridge importer supports:

- Multiple Choice
- Multiple Answer
- True/False
- Matching
- Fill in the Blank
- Fill in Multiple Blanks
- Calculated Numeric
- Calculated Formula
- Essay
- Hot Spot
- Likert

Explicitly not on the list: **Ordering (drag to order)**. Ordering items
are silently dropped on import. The `bb_ultra_qti_v2_1` engine refuses
to emit ORDER items at all (skip with warning) so nothing is silently
lost.

Further empirical finding from the image test round trip: **Hot Spot is
round-trip broken**. An Ultra-authored Hot Spot question cannot be
re-exported - Ultra's exporter writes a warning log file
(`qti21/web_content00001.log` in the image test export) saying:

> Warning: Question Pool Image Test contains 1 questions that could not
> be exported as common cartridge questions. Those questions were
> skipped.

Hot Spot is authorable in Ultra's UI but not round-trip stable through
QTI. For a QTI-focused tool like `qti-package-maker`, Hot Spot is
effectively unsupported and will be treated the same as ORDER if the
codebase ever adds support.

Item types the `qti-package-maker` codebase supports that map cleanly
to Ultra: MC, MA, MATCH, FIB, MULTI_FIB, NUM. These constitute the
production scope of the new engine.

## Tag survival table

All tags tested via Probes 1 and 2. "Survives" means the tag appears
unchanged in Ultra's re-export after a round trip.

### Tags that survive

| Tag | Notes |
| --- | --- |
| `p` | Primary text container |
| `div` | Preserved unchanged; Ultra's own editor wraps itemBody in `<div><div>...</div></div>` |
| `span` | Preserved, but `class=`/`style=` stripped |
| `br` | Preserved, including `<br/><br/>` runs |
| `strong` | Preserved; also the destination for `<b>` rewrites |
| `em` | Preserved; also the destination for `<i>` rewrites |
| `sub` | Preserved |
| `sup` | Preserved |
| `code` | Preserved |
| `ul` | Preserved including nesting |
| `ol` | Preserved including nesting |
| `li` | Preserved |
| `h4` | Preserved, but original `<h4>` gets downshifted to `<h5>` |
| `h5` | Preserved |
| `table` | Preserved and renders as a grid (see table section below) |
| `tbody` | Preserved when present; optional on input |
| `tr` | Preserved |
| `th` | Preserved; optional (all-`<td>` tables render fine) |
| `td` | Preserved |
| `colgroup` | Preserved only in paired form; self-closing form is fatal (see root cause above) |

### Tags Ultra rewrites

| Input | What Ultra does | Engine policy |
| --- | --- | --- |
| `<b>` | Rewrites to `<strong>` | Emit `<strong>` directly |
| `<i>` | Rewrites to `<em>` | Emit `<em>` directly |
| `<u>` | Rewrites to a plain `<span>` - underline is lost | Rewrite to `<span>` during sanitization |
| `<h1>`, `<h2>`, `<h3>` | Downshifted to `<h4>` | Rewrite to `<h4>` during sanitization |
| `<h4>` | Downshifted to `<h5>` | Rewrite to `<h5>` during sanitization |
| `<pre>` | Tag preserved, but whitespace destroyed (tabs, newlines, runs of spaces all collapsed) | Rewrite to `<p>` during sanitization |

### Tags Ultra strips, content preserved

| Tag | Result |
| --- | --- |
| `<blockquote>` | Wrapper removed, children kept |
| `<kbd>` | Wrapper removed, text kept |

### Tags Ultra strips entirely (tag + content)

| Tag | Result |
| --- | --- |
| `<style>` | CSS blocks dropped unconditionally |
| `<script>` | Dropped unconditionally (security) |
| `<hr>` | Dropped unconditionally |
| `<img>` | Structurally broken on Ultra re-export through the `<img src>` path - see "Images" section |

## Attribute stripping

Ultra strips the following attributes from every element, every time,
on re-export:

- `style=` - every CSS declaration, regardless of the property
- `class=` - every class name
- `id=` - element identifiers
- `border`, `cellpadding`, `cellspacing`, `bgcolor`, `align`, `width`,
  `height`, `color`, `face`, `valign` - every deprecated presentational
  attribute on tables, cells, and rows
- event handlers (`onclick`, `onload`, etc.)

The only attribute Ultra preserves on element content is `href` on
anchor tags. Everything else is gone.

**Consequence:** styled cells, colored text, colored backgrounds,
fonts, font sizes, column widths, text alignment, and row heights are
all unportable. Even the Ultra WYSIWYG editor, which appears to support
colored text and font sizes while authoring, strips every `style=`
attribute when its own content is exported. The CSS appearance is a
property of Ultra's rendering pass, not the underlying content model.

## Tables: what works and what does not

This is the biggest finding and the most important for planning.

### What works

Every one of the 12 table structural variants in Probe 2 rendered as a
proper 2-column grid in Ultra's question view, with default gridlines
supplied by Ultra's CSS. The 12 variants were:

1. Control (verbatim copy of the hand-built reference shape)
2. Bare text cells (no wrapping)
3. Clean `<p>`-wrapped cells
4. Multiple `<p>` per cell
5. `<br/>`-separated multiline header
6. Nested empty `<span>` wrappers
7. `<div>` inside cells
8. No `<tbody>`
9. No `<th>` (all `<td>`)
10. Exact shape of the Learn engine's re-export
11. Same shape without `<colgroup>`
12. Legacy `border="1" cellpadding="4" cellspacing="0"` + `<th align="center" width="120">`

Every variant rendered as a proper grid. Ultra's built-in CSS supplies
gridlines, cell padding, and auto-layout. The engine does not need to
emit any layout primitives of its own - pass-through is sufficient.

### What does not work

**Column sizing is not controllable.** Ultra strips every `width=`,
every `style="width:"`, and every `<colgroup width=>` attribute. Column
widths are determined by content and the browser's auto-layout
algorithm. There is no lever to make one column wider than another
short of padding the content with non-breaking spaces, which defeats
the point of having a real table.

**Drawing-canvas tables do not work.** Any HTML table that uses
`colspan`/`rowspan` + per-cell borders + `padding:0` + `visibility:
hidden` spacers to draw a diagram - the sugarlib chemistry library in
the biology-problems repo is the canonical example - cannot render
correctly in Ultra. The tables survive structurally (tags preserved)
but every styling primitive they rely on is stripped, so the "drawing"
collapses to an unreadable grid of fragments. There is no CSS
workaround. The only path for this content is pre-rendering the HTML
to a PNG and embedding the image (see "Images" below, and the deferred
image follow-up project).

### Does this contradict what I thought about the Michaelis-Menten
render?

The Michaelis-Menten render is the exception that proves the rule. The
content was fine; the emitter was wrong. One self-closing `<colgroup/>`
tag broke the HTML5 parser before Ultra's renderer ever got a chance
to draw anything. Once that was isolated (via the double-import test),
the true rule became: Ultra renders tables as grids, always, as long as
the HTML parses.

## Whitespace and entity behavior

### Whitespace

| Construct | Result |
| --- | --- |
| Runs of regular spaces inside `<p>` | Collapsed to a single space |
| Leading/trailing spaces inside `<p>` | Stripped |
| Tab characters (`\t`) anywhere | Converted to single spaces, then collapsed |
| Newlines inside `<pre>` | Collapsed to single spaces (whitespace semantics destroyed) |
| Runs of regular spaces inside `<pre>` | Collapsed to a single space |
| `<br/>` | Preserved, including `<br/><br/>` runs |
| `&#xa0;` (non-breaking space) | Preserved byte-for-byte inside `<p>`, `<span>`, `<td>` |
| Runs of `&#xa0;` | Preserved byte-for-byte |

`<pre>` is functionally equivalent to `<p>` in Ultra. Do not rely on it
for alignment. The new engine rewrites `<pre>` to `<p>` during
sanitization so that no downstream code is misled into thinking `<pre>`
provides a monospace layout primitive.

### Entities

| Input | Re-exported as |
| --- | --- |
| `&lt;`, `&gt;`, `&amp;` | Preserved as `&lt;`, `&gt;`, `&amp;` |
| `&quot;`, `&apos;` | Converted to literal `"`, `'` |
| `&#945;` (decimal numeric) | Converted to literal Unicode (alpha) |
| `&#x03B1;` (hex numeric) | Converted to literal Unicode |
| `&#xa0;` / `&#160;` (nbsp) | Preserved in hex numeric form |

The engine may emit either numeric form for most characters; Ultra
normalizes them to literal Unicode on re-export, which is fine as long
as the output file is UTF-8. Non-breaking space stays numeric because
it has no unambiguous literal representation.

## Images

Three separate image test results; the final gate D re-test below now
produces a working image path.

### Gate D PASS (2026-07-02): Ultra imports and renders images on both paths

Gate D's final verdict is **PASS**. Blackboard Ultra imports and renders
embedded images through both of its import systems: "Import from QTI 2.1
package" (both the `<a href>` and plain `<img>` reference patterns) and
"Import from file" (the `bb_export` conversion path). The earlier
"media-not-imported" reading recorded below was a false negative traced to
the probe image itself, not to Ultra's importers; see "Final status" below
for the full account. `placeholder_warn` was no longer the ceiling for
`bb_ultra_qti_v2_1` once this was confirmed, but rather than upgrade the
dedicated Ultra engine to a `package` media policy, the engine itself was
removed on 2026-07-02: `blackboard_qti_v2_1` and `blackboard_export_zip`
already package and render images in Ultra, making a separate Ultra writer
redundant (see [docs/ENGINES.md](ENGINES.md) for the current supported
Ultra paths and [docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md) gate D for
the verified probe results).

### Final status: `placeholder_warn` is the shipped default (retraction, 2026-07-02)

The engine ships with the `placeholder_warn` media policy: every `<img>` is
replaced with a readable `[image: name.ext]` placeholder text (with an
itemized warning) on a cloned item before sanitization, so authors see a
description of the missing image rather than silence. `placeholder_warn`
was the shipped default through the false-negative gate D round; the
gate D PASS re-test above lifted this limitation, and the dedicated
Ultra engine was subsequently removed rather than upgraded (2026-07-02;
see "Status" note at the top of this document).

Gate D ran on 2026-07-02 against the user's real Blackboard Ultra SaaS
sandbox ("Ultra Sandbox - NVoss"), probing all three of Ultra's available
import paths for the `READ_ONLY/embedded/` pattern documented below (see
[docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md) for the probe kit, import
steps, and results table):

- `ultra_probe_ahref-qti21.zip` ("Import from QTI 2.1 package", `<a href>`
  variant reproducing Ultra's own export pattern): question imported
  successfully, but neither the image nor the anchor text appeared after
  import.
- `ultra_probe_img-qti21.zip` ("Import from QTI 2.1 package", plain `<img>`
  variant): question imported successfully, image did not appear after
  import.
- `ultra_probe_img-bbexport.zip` ("Import from file", `bb_export` conversion
  path): question imported successfully, image did not appear after the
  conversion import.

All three of our own generated packages imported successfully as question
banks with the question text, choices, correct answer, and points intact --
the image did not appear after import on any available path. Whether the
binary was never loaded into the content store or was loaded but not linked
from the question HTML was not determined at the time. At the time, this
was read as proof that Ultra's importers discard embedded media regardless
of route, and `placeholder_warn` was declared final and permanent for
`bb_ultra_qti_v2_1`.

**That conclusion is retracted.** On 2026-07-02, the user imported
`control_ultra-qti21.zip` -- a faithful re-zip of Blackboard's own real
Ultra export (`SAMPLES/blackboard_ultra-qti21_export/`, built by
`devel/build_sample_control_zips.py`, no writer code of ours involved) --
into the same Ultra sandbox, and the embedded image rendered inline (pool
"a blank pool", the MC question's image visible in place). The two
`B-control` Learn imports (see [docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md))
render the same way. All three control packages Blackboard's own exporter
produced render their images on import, so there is no LMS-side ceiling on
media anywhere in this probe matrix: Ultra's (and Learn's) importers handle
embedded media correctly when the package matches Blackboard's own export
shape. The image not appearing after import on every one of our synthesized
packages is therefore a package-shape defect in our own writers, not a
platform limitation.
`placeholder_warn` stayed the shipped default while a root-cause
investigation was open (see
`docs/active_plans/audits/media_import_delta_report.md`); that
investigation concluded in the Gate D PASS finding below, and the
resolution was to remove the dedicated Ultra engine rather than upgrade
it, since the two remaining engines already package and render images in
Ultra.

**Gate D PASS (visible-figure round, 2026-07-02).** The root-cause
investigation found the media-not-imported result was itself a false
negative: the probe figure was a 1x1-pixel test image, real and correctly
imported and linked by Blackboard but too small to see on the page. Two
real writer bugs found during the investigation were also fixed (a QTI 2.1
`correctResponse` `answer_002` vs `answer_2` padding mismatch, and the
`blackboard_export_zip` engine's missing `bbmd_asi_object_id` for
`CSResourceLinks` `parentId`; see `docs/CHANGELOG.md`'s 2026-07-02 "Fixes
and Maintenance"). After rebuilding the probe kits with a visible
240x120 red figure, the user re-imported all three Ultra variants and
every one rendered the image inline: `ultra_probe_ahref-qti21.zip`
(`<a href>` pattern), `ultra_probe_img-qti21.zip` (plain `<img>` pattern),
and `ultra_probe_img-bbexport.zip` ("Import from file" `bb_export`
conversion path). Both the `<a href>` and plain `<img>` QTI 2.1 patterns
render, and Ultra accepts a synthesized `_<digits>_1` id cleanly on every
path. The placeholder-only limitation described throughout this document
is lifted; instead of upgrading the dedicated Ultra engine to a `package`
media policy, the engine was removed (2026-07-02) because
`blackboard_qti_v2_1` and `blackboard_export_zip` already package and
render images in Ultra, making a separate writer redundant. See
[docs/ENGINES.md](ENGINES.md) for current Ultra guidance and
[docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md) gate D for the full
results table and evidence.

### `<img src="csfiles/home_dir/...">` path (tried first)

Probe item 15 attempted to embed a hand-built PNG via
`<img src="csfiles/home_dir/probe_tiny.png">`. Ultra's re-export
replaced the src with a placeholder stub
(`@X@EmbeddedFile.requestUrlStub@X@/bbcswebdavnull`), dropped the PNG
from the ZIP, and turned the self-closing `<img/>` into a container tag
`<img>...</img>` that absorbed following siblings as children. The
output is structurally corrupted and renders as nothing.

### SVG

The user confirmed empirically that SVG content does not render in
Ultra, regardless of how it is embedded. SVG is not a usable format.
Only raster PNG is viable.

### Ultra-native image embedding (pattern confirmed by gate D PASS)

**Note:** the gate-D probe (see "Gate D PASS" above) tested this exact
pattern with a synthesized id. The initial round found the image did not
appear after import, but that was a false negative caused by an invisible
1x1-pixel probe figure, not a defect in the pattern. The visible-figure
retest confirmed the pattern renders correctly on import through both QTI
2.1 import paths and the `bb_export` conversion path. The "deferred to v2"
implementation plan described below never shipped as a dedicated Ultra
engine feature: the engine was removed (2026-07-02) once field evidence
showed `blackboard_qti_v2_1` and `blackboard_export_zip` already package
and render images in Ultra without any Ultra-specific asset-bundling code.
This section remains the reference for the pattern Ultra's own exporter
uses.

The image test at
`ULTRA/image_test/` shows Ultra's canonical
image embedding pattern. A question with an image attachment authored
in Ultra's editor exports as:

```
csfiles/home_dir/                                           (empty sentinel)
READ_ONLY/question/<ultra_question_id>/embedded/<file>.png  (the asset)
qti21/question_bank00001.xml
qti21/assessmentItem00001.xml
imsmanifest.xml
```

The manifest declares the asset as a `webcontent` resource:

```xml
<resource href="READ_ONLY/question/_23159585_1/embedded/L-tagatose.png"
          identifier="ccres00001" type="webcontent">
  <file href="READ_ONLY/question/_23159585_1/embedded/L-tagatose.png"/>
</resource>
```

The item's manifest entry carries a `<dependency>` on the image
resource:

```xml
<resource href="qti21/assessmentItem00001.xml"
          identifier="assessmentItem00001" type="imsqti_item_xmlv2p1">
  <file href="qti21/assessmentItem00001.xml"/>
  <dependency identifierref="ccres00001"/>
</resource>
```

The item body references the asset via a relative path from `qti21/`
back up to `READ_ONLY/`:

```xml
<a href="../READ_ONLY/question/_23159585_1/embedded/L-tagatose.png">
  L-tagatose.png
</a>
```

This pattern is known to round-trip correctly because Ultra itself
produces it. Implementation is deferred to a follow-up image project
because it requires: (a) a local HTML-to-PNG renderer for the biochem
drawing-canvas content; (b) asset bundling in the engine; (c) manifest
resource entries and dependency tracking; (d) item writer integration
that detects drawing-canvas HTML and replaces it with a pre-rendered
image reference; (e) compat gate extensions.

For v1, the engine substitutes a readable `[image: name.ext]` placeholder
into a cloned item before sanitization (with an itemized warning), so the
author sees text describing the missing image rather than nothing. The
sanitizer's unconditional `<img>` drop (below) remains as the backstop for
any `<img>` tag that reaches it, which does not normally happen because the
placeholder substitution runs first.

## QTI shell structural facts

These match the hand-built Ultra sample and the Ultra re-export of the
probe ZIP. They are the shape the new engine emits.

- Manifest namespaces include `imscp_v1p1`, `imsccv1p2/imscsmd_v1p0`,
  `ltsc.ieee.org/xsd/LOM`, `imsqti_metadata_v2p1`.
- `<organizations/>` is empty.
- Resources include one `imsqti_test_xmlv2p1` entry for the test file
  and one `imsqti_item_xmlv2p1` entry per item, with `<dependency>`
  entries linking items to the test.
- Test file path: `qti21/question_bank00001.xml`.
- Test file structure:
  `<assessmentTest>` > `<testPart>` > `<assessmentSection>` > items.
  Ultra renames `assessmentSection/@title` to "Section 1" on re-export
  but keeps everything else.
- Item file path: `qti21/assessmentItemNNNNN.xml`.
- Item `@identifier`: Ultra rewrites every item's identifier to its own
  `QUE__<N>_1` scheme on re-export. CRC16-based identifiers in the
  source are fine and stable.
- Item body wrapping: Ultra's editor wraps content in
  `<div><div>...</div></div>`. The new engine emits this pattern.
- `simpleChoice` content wrapping: Ultra's editor wraps choice content
  in `<div><p>...</p></div>`. The new engine emits this pattern.
- `responseDeclaration cardinality="multiple" baseType="identifier"`
  for every MC and MA, with unpadded `answer_N` identifiers that match
  each `simpleChoice/@identifier` exactly.
- `outcomeDeclaration` triple: `SCORE` (float, default 0),
  `FEEDBACKBASIC` (identifier), `MAXSCORE` (float, default 0).
- `responseProcessing`: full `<responseIf><match/><setOutcomeValue/>`
  setting `SCORE` from `MAXSCORE` and `FEEDBACKBASIC` to `correct_fb`,
  plus `<responseElse>` setting `FEEDBACKBASIC` to `incorrect_fb`.
- `choiceInteraction shuffle="false"`.
- `csfiles/home_dir/` empty directory must exist in the ZIP.

## Engine sanitizer rules (locked)

The removed `bb_ultra_qti_v2_1` engine's HTML sanitizer implemented these
rules (see `qti_package_maker/engines/bb_ultra_qti_v2_1/html_sanitize.py`
in the pre-removal git history, deleted 2026-07-02).

**Core operation.** Every input HTML fragment is re-serialized through
`lxml.html.fromstring` + `lxml.html.tostring`. This single operation
repairs self-closing non-void tags (like the `<colgroup width="160"/>`
that caused the Michaelis-Menten collapse) uniformly. Nothing else in
the sanitizer matters without this pass.

**Tag allowlist:**
`p`, `div`, `span`, `br`, `em`, `strong`, `sub`, `sup`, `code`, `ul`,
`ol`, `li`, `h4`, `h5`, `table`, `tbody`, `tr`, `th`, `td`, `colgroup`,
`col`, `a`.

**Tag rewrites:**
`<b>` -> `<strong>`, `<i>` -> `<em>`, `<u>` -> `<span>`, `<h1>`/`<h2>`/
`<h3>` -> `<h4>`, `<h4>` -> `<h5>`, `<pre>` -> `<p>`.

**Tag unwraps (tag removed, content kept):**
`<blockquote>`, `<kbd>`, any tag not on the allowlist and not in the
drop list.

**Tag drops (tag and content removed):**
`<style>`, `<script>`, `<img>`. A placeholder-text substitution runs upstream
of the sanitizer (see the Images section above), so a live `<img>` tag
normally never reaches this drop rule.

**Attribute strips (removed unconditionally from every element):**
`style`, `class`, `id`, `cellpadding`, `cellspacing`, `bgcolor`,
`border`, `align`, `width`, `height`, `color`, `face`, `valign`, any
attribute starting with `on`, any attribute containing `:`. The only
exception is `href` on `<a>` elements.

**What the sanitizer does NOT do:**
- Does not rewrite `<div>` to `<p>`. Ultra preserves `<div>`.
- Does not wrap bare cell text in `<p>`. Probe showed it is not
  required.
- Does not collapse nested empty spans.
- Does not normalize table structure.

**Idempotence:** `sanitize(sanitize(x)) == sanitize(x)` for every
fixture. Was unit-tested in `tests/test_ultra_html_sanitize.py` (deleted
2026-07-02 with the engine; see pre-removal git history).

## Render correctness vs round-trip stability

A construct is only a stable feature of the engine if it survives
import -> render -> export -> re-import unchanged. Import tolerance
(Ultra accepts wide, emits narrow) is not a feature contract. The
emitted subset is the contract.

| Probe dimension | Round-trip stable? | Renders correctly? | Notes |
| --- | --- | --- | --- |
| `<pre>` | Tag yes, semantics no | NO | Whitespace destroyed, rewrite to `<p>` |
| nbsp columns | YES | YES | Useful for in-line spacing only, not tables |
| `<br/>` runs | YES | YES | |
| Plain `<table>` grid | YES | YES | Native Ultra rendering, no layout hack needed |
| `<table>` cell shape variants (12 tested) | YES | YES | Every variant |
| Whitespace stress (tabs, space runs) | Collapsed | N/A | Lost |
| Legacy `<table>` attributes | Stripped | N/A | Engine drops |
| Inline formatting (`em`, `strong`, `sub`, `sup`, `code`) | YES | YES | |
| `<u>` | Rewritten to `<span>` | Underline lost | |
| `<kbd>` | Stripped | Content survives | |
| `<div>` vs `<p>` | YES both | YES both | |
| Entities | Normalized to Unicode | YES | UTF-8 output |
| Lists (nested) | YES | YES | |
| Headings | Shifted down 1 level | Rendered at shifted level | |
| CSS (inline, style tag, class) | NO, all stripped | NO | Unportable |
| `<img src="csfiles/...">` | Structurally broken | NO | Strip unconditionally |
| SVG | - | NO | Not supported in Ultra |
| `<img>` via `READ_ONLY/embedded/` path | YES (confirmed) | YES -- renders on import of a synthesized id, both QTI 2.1 patterns and the `bb_export` conversion path (gate D PASS, visible-figure round, 2026-07-02) | Served today by `blackboard_qti_v2_1` and `blackboard_export_zip` (dedicated Ultra engine removed 2026-07-02); see "Gate D PASS" above |

## What this means for old Learn content

A rough porting forecast based on the above:

| Learn content type | Ultra port outcome |
| --- | --- |
| Prose questions (MC, MA, FIB, NUM, MULTI_FIB, MATCH) | Clean port |
| Data tables (Michaelis-Menten, gels, numeric results) | Clean port once the colgroup bug is avoided |
| Colored text, highlighted cells, font sizes | Styling lost; meaning lost if color-coded |
| Tabular data with fixed column widths | Layout is content-driven; fixed widths are impossible |
| Chemistry diagrams drawn with HTML tables (sugarlib class) | Does not work in v1; deferred to image project |
| Ordering / drag-to-order questions | Not supported by Ultra; engine refuses to emit |
| Hot Spot questions | Authorable in Ultra but cannot round-trip |
| Questions with inline `<img>` images | Clean port -- gate D PASS (visible-figure round, 2026-07-02) confirmed the image renders on import through both QTI 2.1 patterns and the `bb_export` conversion path; served today by `blackboard_qti_v2_1` and `blackboard_export_zip` |
| Questions using `<u>` for underline | Underline lost on import |
| Questions using `<pre>` for monospace layout | Whitespace destroyed; rewrite to `<p>` |
| Multi-heading questions | Headings downshift by one level (h3 -> h4, h4 -> h5) |

## Deferred: image follow-up project

**Note:** gate D PASS (visible-figure round, 2026-07-02, see "Gate D PASS"
above) confirmed the `READ_ONLY/embedded/` asset-bundling pattern below
renders correctly on import with a synthesized id, on every one of our own
generated packages, through both QTI 2.1 import paths and the `bb_export`
conversion path. Plain `<img>` embedding into Ultra is a solved problem via
`blackboard_qti_v2_1` and `blackboard_export_zip` (no dedicated Ultra
asset-bundling code was ever needed); the dedicated Ultra engine that would
have implemented this pattern was removed 2026-07-02 as redundant. This
section remains the reference for the asset-bundling shape Ultra's own
exporter uses, for anyone who later needs it.

Content that depends on pre-rendered or embedded images - specifically
the biochem drawing-canvas question generators in the
biology-problems repo - still requires a follow-up project that remains
out of scope for this repo. The charter for that project is in the plan at
`/Users/vosslab/.claude/plans/dreamy-dancing-sparrow.md` under
"Follow-up project: Ultra image asset support" (a historical reference;
that plan predates the engine removal). Summary of what it would need to
build, if picked up by whichever engine(s) end up carrying it:

1. A local HTML-to-PNG renderer (headless browser or weasyprint).
2. Asset bundling in the engine: files written to
   `READ_ONLY/question/<id>/embedded/<filename>`, declared as
   `webcontent` resources in the manifest, linked to items via
   `<dependency>`.
3. Writer integration that detects drawing-canvas HTML (heuristic:
   `colspan` or `rowspan` combined with `style="padding:0"` or per-edge
   borders) and replaces the table with an `<img>` reference and a
   bundled asset.
4. Compat gate extensions that hard-fail on any image reference
   without a matching bundled asset and dependency.

PNG only. SVG is not a viable format in Ultra. Revisit SVG only if a
future Ultra release adds support.

## Generated manifest vs. canonical reference

The `bb_ultra_qti_v2_1` engine's manifest (`imsmanifest.xml`) and test
file (`qti21/question_bank00001.xml`) are audited against the canonical
Ultra re-export shapes obtained from the probe round-trip (`ULTRA/ultra_probe-roundtrip/`).

### Audit methodology

The manifest and question_bank builders in `assessment_meta.py` are tested
in isolation by calling `generate_manifest(2)` and `generate_question_bank(2)`
directly, which returns lxml.etree ElementTree objects suitable for comparison.
The generated XML is serialized and compared byte-for-byte against the
canonical reference (`ULTRA/ultra_probe-roundtrip/imsmanifest.xml` and
`.../question_bank00001.xml`) after accounting for acceptable formatting
differences.

### Audit findings

**No structural differences.** The manifest and question_bank builders produce
the correct XML shape:

- **imsmanifest.xml:**
  - Namespaces: all five declared (xmlns, xmlns:csm, xmlns:imsmd, xmlns:imsqti, xmlns:xsi)
  - xsi:schemaLocation: correct (9-element list)
  - metadata block: schema="QTIv2.1", schemaversion="2.0"
  - organizations: empty, self-closing
  - resources structure: test resource (identifier="question_bank00001", type="imsqti_test_xmlv2p1") listed FIRST, with dependencies on all items; item resources (type="imsqti_item_xmlv2p1") follow
  - file href attributes: use "qti21/filename" paths from root

- **qti21/question_bank00001.xml:**
  - Namespaces: xmlns and xmlns:xsi declared
  - xsi:schemaLocation: correct
  - Root element: identifier="question_bank00001", title attribute present
  - Nesting: testPart > assessmentSection (identifier="question_bank00001_1_1")
  - assessmentItemRef elements: href uses relative paths (e.g., "assessmentItem00001.xml") without the qti21/ prefix

### Acceptable differences

1. **assessmentTest @title:** generated uses "Test Bank" (generic default); canonical uses "Ultra Probe" (specific to the probe package). The engine cannot infer a meaningful test title from an ItemBank object. This default is acceptable and matches common LMS conventions.

2. **Formatting:** lxml's pretty_print adds whitespace; canonical is minified. Both parse identically under XML parsers.

3. **Quote style:** lxml emits single quotes in the XML declaration; canonical uses double quotes. Both are valid XML.

4. **Item identifier rewrites on re-export:** Ultra rewrites all identifiers to its own scheme on import; both our generated and the canonical reference use sequential numbered identifiers (assessmentItem00001, etc.) which Ultra is known to replace. This is expected and acceptable per M7 requirements.

### Conclusion

The engine's manifest builders produce structurally identical output to
Ultra's native export format. No fixes are required. The title
difference is documented as intentional and acceptable.
