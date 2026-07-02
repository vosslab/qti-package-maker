# Media LMS import probes

Purpose, build commands, and manual import steps for the real-LMS probe
kits that back the image-support plan's formal gates. Every kit's ZIP
layout and manifest shape is proven by an automated fixture
([tests/integration/test_probe_package_structure.py](../tests/integration/test_probe_package_structure.py))
before any human import; only real-LMS rendering waits on a sandbox. See
[docs/active_plans/active/image_support_plan.md](active_plans/active/image_support_plan.md)
for the full plan, and
[docs/BLACKBOARD_ULTRA_NOTES.md](BLACKBOARD_ULTRA_NOTES.md) for the prior
Ultra empirical findings this probe extends.

## Gate A: Canvas Classic Quizzes `<img src>` token

Confirms whether Canvas Classic Quizzes resolves a plain relative
`<img src>` on QTI 1.2 import, or requires the `$IMS-CC-FILEBASE$` token
Canvas's own exports use (see the image support plan's "Evidence summary").
No real Canvas image export sample exists yet, so this kit's expected
structure is derived from the QTI 1.2 spec and text2qti prior art rather
than a `SAMPLES/` reference.

**Status: BLOCKED** -- no Canvas sandbox available (Instructure discontinued
the Free for Teacher program, noted 2026-07-02). Per the plan's documented
fallback for an inconclusive gate A, the `canvas_qti_v1_2` engine ships the
spec-relative `<img src>` variant as its default
(`CANVAS_SRC_VARIANT_RELATIVE`); the `$IMS-CC-FILEBASE$` variant remains
selectable via the engine's `canvas_src_variant` constructor kwarg. Anyone
with institutional Canvas access can still run this probe with the existing
kit (`devel/build_canvas_media_probe.py`) and record results in the table
below.

Build:

```bash
source source_me.sh && python3 devel/build_canvas_media_probe.py -o output_probes/canvas
```

Writes two ZIPs:

- `output_probes/canvas/canvas_probe_relative.zip` -- `<img src="../media/probe-figure.jpg">`
- `output_probes/canvas/canvas_probe_filebase.zip` -- `<img src="$IMS-CC-FILEBASE$/media/probe-figure.jpg">`

Import steps (Canvas Classic Quizzes sandbox):

1. Course Settings > Import Course Content > Content Type: "QTI .zip file".
2. Upload `canvas_probe_relative.zip`; wait for the import job to finish.
3. Open the imported quiz and view the one multiple-choice question; record
   whether the probe image renders.
4. Repeat steps 2-3 with `canvas_probe_filebase.zip`.
5. Record both outcomes in the results table below.

## Gate B (OPTIONAL): Blackboard Learn CLASSIC image import, both paths

**Status: PASS (optional).** Both classic Blackboard Learn import paths --
Pools import of the `blackboard_export_zip` output, and QTI 2.1 import of
the `blackboard_qti_v2_1` output -- rendered the probe image and marked the
correct answer on the human-verified 2026-07-02 visible-figure re-import.
See the visible-figure-retest rows in the results table below.

Convenience verification only -- both writers this gate probes are already
evidenced directly from `SAMPLES/blackboard_learn_classic-bb_export` and
`SAMPLES/blackboard_learn_classic-qti21_export` plus their in-code
write/read roundtrip tests, so they ship on that evidence without waiting
on this gate. Classic Blackboard Learn exposes two separate pool/question
import paths, so `devel/build_bb_original_probe.py` builds a real probe ZIP
through each engine, format-suffixed and titled so the two imports are
never indistinguishable in the Learn UI:

```bash
source source_me.sh && python3 devel/build_bb_original_probe.py -o output_probes/bb_learn
```

Writes two ZIPs:

- `output_probes/bb_learn/bb_learn_probe_img-bbexport.zip` -- one MC item
  whose question stem embeds the probe image via the `blackboard_export_zip`
  engine's csfiles image-embedding path
  (`csfiles/home_dir` binary + `.jpg.xml` LOM sidecar, `res00005.dat`
  CSResourceLinks entry, `@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1`
  body token), and imports as pool title "BB Learn Probe IMG BBEXPORT".
  Targets Course Tools > Import Package / View Logs > Import Package (the
  Blackboard Original `bb_export` importer).
- `output_probes/bb_learn/bb_learn_probe_img-qti21.zip` -- the same probe
  question built through the `blackboard_qti_v2_1` engine's root-level image
  write path (image staged at the package root, `<img src>` rewritten with a
  single `../`, webcontent resource wired to the item via `<dependency>`),
  and imports as pool title "BB Learn Probe IMG QTI21". Targets Course
  Tools > Tests, Surveys and Pools > Pools > Import (the QTI 2.1 importer).

Import steps (Blackboard Learn Original sandbox):

1. Course Tools > Import Package / View Logs > Import Package. Upload
   `bb_learn_probe_img-bbexport.zip`; wait for the import job to finish.
2. Open the imported pool question; record whether the probe image renders.
3. Course Tools > Tests, Surveys and Pools > Pools > Import. Upload
   `bb_learn_probe_img-qti21.zip`; wait for the import job to finish.
4. Open the imported pool question; record whether the probe image renders.
5. Record both outcomes in the results table below.

## Gate D: Blackboard Ultra synthesized-id image import

**Status: PASS.** Both the `<a href>` and plain `<img>` QTI 2.1 patterns
render inline in Ultra, and Ultra's "Import from file" `bb_export`
conversion path also renders; a synthesized `_<digits>_1` id imports
cleanly on every path. See "Final verdict (visible-figure round,
2026-07-02)" below and the visible-figure-retest rows in the results
table.

Blackboard Ultra exposes two separate import systems, so this gate probes
both. "Import from QTI 2.1 package" confirms whether an Ultra import
accepts a `READ_ONLY/question/_<digits>_1/` image reference whose id we
mint ourselves, rather than an id Ultra assigned during its own export.
Ultra's `<a href>` degradation pattern rendering when Ultra itself produced
the id is already confirmed (see
[docs/BLACKBOARD_ULTRA_NOTES.md](BLACKBOARD_ULTRA_NOTES.md) "Ultra-native
image embedding"); this gate tests the one open question -- import of a
package with a synthesized id -- plus a second variant that substitutes a
plain `<img>` tag for the `<a href>` link, in case Ultra's importer treats
the two differently. "Import from file" is a separate menu entry that
accepts a Blackboard Original `bb_export` package and converts it on
import; a third variant probes whether the embedded figure survives that
conversion.

Build:

```bash
source source_me.sh && python3 devel/build_ultra_media_probe.py -o output_probes/ultra
```

Writes three ZIPs. Every ZIP's filename carries a format suffix and imports
with a matching, visible pool title, so none of the three question banks
are indistinguishable in the Ultra UI. The two QTI 2.1 variants share the
synthesized question id `_90000001_1` (the leading `9` distinguishes it
from any real Blackboard-assigned id):

- `output_probes/ultra/ultra_probe_ahref-qti21.zip` -- targets Ultra's
  "Import from QTI 2.1 package" menu entry; reproduces Ultra's own export
  degradation pattern, `<a href="../READ_ONLY/question/_90000001_1/embedded/image-1.jpg">image-1.jpg</a>`,
  and imports as pool title "Ultra Media Probe AHREF QTI21"
- `output_probes/ultra/ultra_probe_img-qti21.zip` -- targets Ultra's
  "Import from QTI 2.1 package" menu entry; substitutes a plain
  `<img src="../READ_ONLY/question/_90000001_1/embedded/image-1.jpg" alt="image-1.jpg"/>` tag,
  and imports as pool title "Ultra Media Probe IMG QTI21"
- `output_probes/ultra/ultra_probe_img-bbexport.zip` -- targets Ultra's
  "Import from file" menu entry (the bb_export conversion importer); built
  through the real `blackboard_export_zip` engine's csfiles image-embedding
  write path (the same path gate B's kit exercises), and imports as pool
  title "Ultra Media Probe IMG BBEXPORT"

Import steps (Blackboard Ultra sandbox):

1. Course Content > Question Banks / Pools > Import Content > "Import from
   QTI 2.1 package".
2. Upload `ultra_probe_ahref-qti21.zip`; wait for the import job to finish.
3. Open the imported question; record whether the linked/embedded image
   renders (the a-href variant surfaces as a clickable link to the image
   file unless Ultra inlines it).
4. Repeat steps 2-3 with `ultra_probe_img-qti21.zip`.
5. Course Content > Question Banks / Pools > Import Content > "Import from
   file". Upload `ultra_probe_img-bbexport.zip`; wait for the conversion
   import job to finish, open the imported question, and record whether the
   embedded figure survives conversion.
6. Record all three outcomes in the results table below.

## Results

Fill in after each sandbox import. `Evidence` is a screenshot path or
export-log excerpt saved under `ULTRA/` or an equivalent local evidence
folder (not committed unless small and intentional, per
[docs/REPO_STYLE.md](REPO_STYLE.md#data-and-outputs)).

| Gate | Variant | Date | LMS version | Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| A | relative src | | | | |
| A | `$IMS-CC-FILEBASE$` src | | | | |
| B (optional) | bbexport (`bb_learn_probe_img-bbexport.zip`) | 2026-07-02 | Blackboard Learn Original (sandbox) | media-not-imported | user import log, 2026-07-02 (question and answer imported fine; a resource-link warning was logged on the first import, before the `bbmd_asi_object_id` fix landed the same day; re-test after the fix pending a fresh import log) |
| B (optional) | qti21 (`bb_learn_probe_img-qti21.zip`) | 2026-07-02 | Blackboard Learn Original (sandbox) | media-not-imported | user import log, 2026-07-02 (question now saves with the correct answer after the unpadded-`answer_id` fix and re-import; image still does not appear) |
| B-control | real Learn export re-zip, bbexport path (`control_learn-bbexport.zip`) | 2026-07-02 | Blackboard Learn Original (sandbox) | renders | user report, 2026-07-02 |
| B-control | real Learn export re-zip, qti21 path (`control_learn-qti21.zip`) | 2026-07-02 | Blackboard Learn Original (sandbox) | renders | user report, 2026-07-02 |
| D | a-href (QTI 2.1) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | media-not-imported | user screenshots, 2026-07-02 (question intact, no image, no link) |
| D | `<img>` (QTI 2.1) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | media-not-imported | user screenshots, 2026-07-02 (question intact, no image, no link) |
| D | bb_export via Ultra conversion (`ultra_probe_img-bbexport.zip`) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | media-not-imported | user screenshots, 2026-07-02 (question intact, no image, no link) |
| D-control | real Ultra export re-zip (`control_ultra-qti21.zip`) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | renders | user screenshot (pool "a blank pool", image inline) |
| B (optional), visible-figure retest | bbexport (`bb_learn_probe_img-bbexport.zip`), Pools import | 2026-07-02 | Blackboard Learn Original (sandbox) | renders | user screenshot, 2026-07-02 (visible 240x120 red figure renders; correct answer marked) |
| B (optional), visible-figure retest | qti21 (`bb_learn_probe_img-qti21.zip`), QTI 2.1 import | 2026-07-02 | Blackboard Learn Original (sandbox) | renders | user screenshot, 2026-07-02 (image renders; correct answer marked; question title `QUE_cd08_e73a_be40`) |
| D, visible-figure retest | a-href (QTI 2.1) (`ultra_probe_ahref-qti21.zip`) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | renders | user screenshot, 2026-07-02 (image renders inline) |
| D, visible-figure retest | `<img>` (QTI 2.1) (`ultra_probe_img-qti21.zip`) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | renders | user screenshot, 2026-07-02 (image renders inline) |
| D, visible-figure retest | bb_export via "Import from file" (`ultra_probe_img-bbexport.zip`) | 2026-07-02 | Blackboard Ultra SaaS (sandbox) | renders | user screenshot, 2026-07-02 (image renders inline) |
| D, bonus cross-import | `ultra_probe_img-bbexport.zip` imported into Learn Classic instead of Ultra | 2026-07-02 | Blackboard Learn Original (sandbox) | renders | user screenshot, 2026-07-02 (same `blackboard_export_zip` engine output renders in both Learn and Ultra) |

`Result` values: `renders`, `broken-link`, `import-rejected`,
`media-not-imported`, `not-yet-tested`. `media-not-imported` means the image
does not appear after import; whether the binary was never loaded into the
content store or was loaded but not linked from the question HTML is
undetermined.

**Gate B verdict:** our two generated probe variants (bbexport and qti21)
both imported the question cleanly, but the image does not appear after
import on either path, matching gate D's pattern. The two `B-control` rows --
faithful re-zips of Blackboard's own real Learn exports
(`SAMPLES/blackboard_learn_classic-bb_export/`,
`SAMPLES/blackboard_learn_classic-qti21_export/`, built by
`devel/build_sample_control_zips.py`) imported into the same sandbox -- both
render their images. This proves the Learn Original import paths themselves
carry media fine; the media-not-imported result on our own bbexport and
qti21 rows is a package-shape delta in our writers, not a platform ceiling.
See `docs/active_plans/audits/media_import_delta_report.md` (in progress)
for the root-cause investigation.

**Gate B final verdict (visible-figure round, 2026-07-02): PASS.** The
media-not-imported result above turned out to be a false negative, not a
package-shape defect. The root-cause investigation traced it to the probe
figure itself: a 1x1-pixel test image that Blackboard imported and linked
correctly but that was invisible on the page, costing a full day of false
"image not imported" verdicts. Two real writer bugs were also found and
fixed along the way (a QTI 2.1 `correctResponse` `answer_002` vs
`answer_2` padding mismatch, and the `blackboard_export_zip` engine's
missing `bbmd_asi_object_id` for `CSResourceLinks` `parentId`, both listed
in `docs/CHANGELOG.md`'s 2026-07-02 "Fixes and Maintenance"). After
rebuilding the probe kits with a visible 240x120 red figure and re-testing
both Learn Classic import paths, both `bb_learn_probe_img-bbexport.zip`
(Pools import) and `bb_learn_probe_img-qti21.zip` (QTI 2.1 import)
rendered the image and marked the correct answer. See the
visible-figure-retest rows above.

**Gate D verdict:** all three of our generated variants imported cleanly as
question banks (question text, choices, correct answer, and points all
intact), but the image did not appear after import on any path -- the QTI
2.1 importer produced no visible `<a href>` link (including its anchor
text) or plain `<img>` tag, and the "Import from file" conversion path also
produced no visible csfiles-embedded image. The `D-control` row -- a
faithful re-zip of Blackboard's own real Ultra export
(`SAMPLES/blackboard_ultra-qti21_export/`, built by
`devel/build_sample_control_zips.py`) imported into the same Ultra sandbox --
renders its image inline. Combined with the two Learn `B-control` renders
above, all three control packages Blackboard's own exporter produced render
their images on import: there is no LMS ceiling on media anywhere in this
probe matrix. The "Ultra strips media" conclusion recorded after the
initial gate D run is retracted; the media-not-imported result on our
synthesized packages (gates B and D alike) is a package-shape defect in our
own writers, not a platform limitation. Root-cause investigation is open;
see `docs/active_plans/audits/media_import_delta_report.md` (in progress)
and `docs/BLACKBOARD_ULTRA_NOTES.md` "Final status" for the corrected
framing.

**Gate D final verdict (visible-figure round, 2026-07-02): PASS.** The
"package-shape defect" framing above is superseded: the root-cause
investigation found the media-not-imported result was a false negative
caused by the probe figure being a 1x1-pixel test image, invisible on the
page even though Blackboard imported and linked it correctly. The two real
writer bugs found and fixed during the investigation (the QTI 2.1
`correctResponse` padding mismatch and the `blackboard_export_zip` missing
`bbmd_asi_object_id`, both in `docs/CHANGELOG.md`'s 2026-07-02 "Fixes and
Maintenance") also needed fixing, but were independent of the visibility
issue. After rebuilding the probe kits with a visible 240x120 red figure
(`devel/build_ultra_media_probe.py`, `devel/build_bb_original_probe.py`),
the user re-imported all three Ultra variants and every one rendered the
image inline: `ultra_probe_ahref-qti21.zip` (a-href pattern),
`ultra_probe_img-qti21.zip` (plain `<img>` pattern), and
`ultra_probe_img-bbexport.zip` ("Import from file" `bb_export` conversion
path). Both the a-href and plain `<img>` QTI 2.1 patterns render, and a
synthesized `_<digits>_1` id imports cleanly on every path. As a bonus
cross-import check, `ultra_probe_img-bbexport.zip` (built for Ultra) was
also imported directly into Learn Classic and rendered there too,
confirming the `blackboard_export_zip` engine's image-embedding output
ports across both Learn Original and Ultra. See the visible-figure-retest
and bonus cross-import rows above.

## Automated structure proof

`tests/integration/test_probe_package_structure.py` builds each kit
(Canvas, Ultra, BB Learn CLASSIC) into `tmp_path`, unzips it, and asserts:

- the image bytes land at the expected archive path with unmodified content;
- for Canvas, the BB Learn qti21 variant, and the two Ultra QTI 2.1
  variants: the manifest declares exactly one `webcontent` resource for the
  image, with the expected `href`, and the referencing item resource
  carries a `<dependency>` on it; the item XML embeds the expected
  `<img src>` or `<a href>` token for its variant;
- for the BB Learn bbexport variant and the Ultra bbexport variant (both
  built through the same `blackboard_export_zip` engine write path): the
  csfiles binary and its LOM sidecar are both present, the pool `.dat` body
  carries the matching `@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1`
  token, `res00005.dat` CSResourceLinks records the matching `resourceId`,
  and `imsmanifest.xml` does not declare the csfiles files (implicit
  bundling), matching the shapes in `tests/fixtures/bb_export_slice/` (the
  trimmed real-export reference).

For gate D's QTI 2.1 pair, a companion test parses the real
`SAMPLES/blackboard_ultra-qti21_export/imsmanifest.xml` and asserts the
same webcontent/dependency shape holds there, so the probe kit's structure
is checked against the real sample it is meant to replicate, not just
against itself.

Run:

```bash
source source_me.sh && pytest tests/integration/test_probe_package_structure.py -q
```
