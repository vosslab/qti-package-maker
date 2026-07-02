# Media import delta report

Field-level comparison of qti-package-maker output packages against real
Blackboard-produced exports, investigating why imported questions appeared to
have images not loaded. Read-only investigation. No code was changed.

## Primary finding: the probe asset was the false negative

The apparent "missing image" was, at least for bb_export, a correctly imported
but visually invisible image. Every probe figure in these packages is a minimal
1x1-pixel JPEG. When Learn served our imported bb_export image it returned that
exact 633-byte 1x1 JPEG; it rendered as an invisible dot, which read as a
"missing" or "tiny broken" image in screenshots.

Probe asset dimensions (from `file`):

| Package | Embedded image | Dimensions | Bytes |
| --- | --- | --- | --- |
| Ours bb_export | `csfiles/home_dir/__xid-1_1.jpg` | 1x1 | 633 |
| Ours Learn qti21 | `probe-figure.jpg` | 1x1 | ~633 |
| Ours Ultra img qti21 | `READ_ONLY/.../embedded/image-1.jpg` | 1x1 | 633 |
| Ours Ultra ahref qti21 | `READ_ONLY/.../embedded/image-1.jpg` | 1x1 | 633 |
| Real bb_export | `csfiles/home_dir/__xid-23446236_1.jpg` | 1280x853 | 406646 |

Confirmed end-to-end facts for bb_export (from the imported course):

- Learn rewrote the body token to
  `<img src="https://.../bbcswebdav/xid-23448691_1" alt="probe figure" />` with
  a fresh server-assigned xid, and the `alt` text survived. The full `<img>`
  element round-tripped; the body reference was linked (not FP2).
- Resolving that rewritten xid URL served our 1x1 JPEG (633 bytes). A
  content-store record was created and the binary payload attached and served
  (not FP1).

Conclusion: the bb_export pipeline works end-to-end after today's
CSResourceLinks `parentId` fix. The primary source of the "images not loaded"
report was the 1x1 probe asset, not a package delta. A probe rebuild with a
visible figure is the real test for the remaining formats.

## Framing (failure points)

For a media reference that reaches the importer:

- FP1 not ingested: the binary is never written into the platform content
  store; no served URL exists. bb_export is now shown NOT to be FP1.
- FP2 not linked (dangling src): binary ingested but the question HTML
  reference is never rewired. bb_export is shown NOT to be FP2 (token rewritten,
  alt preserved).
- FP3 display suppressed / invisible: reference intact and file served, but
  nothing visible. A 1x1 image is the degenerate case of "served but invisible"
  and is the confirmed bb_export explanation.

## Method and files inspected

Probe zips unzipped into a scratch directory; SAMPLES trees read in place.
Binary-detected `.dat` files pretty-printed with `xmllint --format`.

```
unzip -o output_probes/bb_learn/bb_learn_probe_img-bbexport.zip -d <scratch>/bbexport_ours
unzip -o output_probes/bb_learn/bb_learn_probe_img-qti21.zip   -d <scratch>/qti21_ours
unzip -o output_probes/ultra/ultra_probe_img-qti21.zip         -d <scratch>/ultra_img_ours
unzip -o output_probes/ultra/ultra_probe_ahref-qti21.zip       -d <scratch>/ultra_ahref_ours
xmllint --format <scratch>/bbexport_ours/res00002.dat > <scratch>/pretty/ours_pool.xml
xmllint --format SAMPLES/blackboard_learn_classic-bb_export/res00002.dat > <scratch>/pretty/real_pool.xml
file <scratch>/bbexport_ours/csfiles/home_dir/__xid-1_1.jpg   # -> 1x1 JPEG, 633 bytes
```

Files compared: bb_export `imsmanifest.xml`, `.bb-package-info`, `.bb-log-info`,
`.bb-package-sig`, `res00001.dat`, `res00002.dat`, `res00005.dat`,
`csfiles/home_dir/__xid-*.jpg(.xml)`, `res00002/<hash>/image-30.jpg`; Learn
qti21 `imsmanifest.xml`, `qti21_items/` vs `qti21/` XML, root `image-*.jpg`;
Ultra qti21 `imsmanifest.xml`, `qti21/*.xml`, `READ_ONLY/question/_<id>_1/embedded/*.jpg`.

## Reclassification key

Given the bb_export end-to-end success, deltas are re-tagged as:

- PROVEN-BENIGN: bb_export ingestion+linking demonstrably worked despite this
  delta, so it does not block media on that path.
- UNTESTED-CANDIDATE: could still matter for Learn qti21 or Ultra, which were
  not URL-resolved; keep for the next import round.
- HARDENING: safe to align with the real export for robustness; no evidence it
  blocks anything.
- COSMETIC: value-only or presentation differences.

## Pair A: bb_export (assessment/x-bb-qti-pool)

bb_export is confirmed working end-to-end. All A-series deltas below are
therefore PROVEN-BENIGN for ingestion/linking, or HARDENING/COSMETIC.

### A1. imsmanifest.xml

| Surface | Ours | Real | Class |
| --- | --- | --- | --- |
| res00001 child | `<file href="/res00001"/>` present | no child file | COSMETIC |
| res00002 (pool) child | none | `<file href="<hash>/image-30.jpg"/>` | HARDENING |
| res00002 companion dir | absent | `res00002/<hash>/image-30.jpg` | HARDENING |
| bb:title on res00001 | package name | course display name | COSMETIC |

The real package-local embed (`<file>` child + `res00002/<hash>/` +
`matapplication`) is a second, independent image mechanism. Our CS/bbcswebdav
path works without it, so it is HARDENING, not required.

### A2. .bb-package-info

| Field | Ours | Real | Class |
| --- | --- | --- | --- |
| cx.config.course.id | absent | `D7.202320` | PROVEN-BENIGN |
| app.release.number | `qti-package-maker` | Learn build string | COSMETIC |
| cx.config.full.value (CxConfig) | absent | full | COSMETIC |
| learn.installation.id / site.id | absent | present | COSMETIC |
| package.identifier | absent | 32-hex | COSMETIC |
| cx.package.info.version | `6.0` | `6.0` | match |
| db.* / java.* / os.* | absent | present | COSMETIC |

The absent `cx.config.course.id` did not block ingestion; Learn assigned the
CS record into the target course regardless. PROVEN-BENIGN.

### A3. .bb-log-info and .bb-package-sig

| Item | Ours | Real | Class |
| --- | --- | --- | --- |
| .bb-log-info | generic lines | course PkId line | COSMETIC |
| .bb-package-sig | absent | 32-hex signature | COSMETIC |

### A4. res00002.dat pool item body and image mechanisms

| Surface | Ours | Real | Class |
| --- | --- | --- | --- |
| mat_formattedtext type | `SMART_TEXT` | `HTML` | PROVEN-BENIGN |
| img tag form | `<img .../>` self-closed | `<img ...>` HTML void + style | COSMETIC |
| img wrapper | bare | `<p>...<br>...<br>&nbsp;</p>` | COSMETIC |
| inline src token | `...bbcswebdav/xid-1_1` | `...bbcswebdav/xid-23446236_1` | see A6 |
| second mechanism | none | `<matapplication uri="<hash>/image-30.jpg" embedded="Inline">` | HARDENING |
| item title attr | absent | `title="MC test"` | COSMETIC |
| bbmd_partialcredit | empty | `false` | COSMETIC |
| bbmd_is_metadataenabled | empty | `false` | COSMETIC |
| bbmd_asi_object_id | `_3439912762_1` | `_23221280_1` | COSMETIC (value) |
| other bbmd_* | same names/values | same | match |

Important correction: `SMART_TEXT` did NOT block the image. Learn still parsed
the `@X@EmbeddedFile...bbcswebdav/xid-N` token, rewrote it to a fresh xid, and
preserved `alt`. The earlier hypothesis that HTML-vs-SMART_TEXT gates media
rewiring is disproven for this path. PROVEN-BENIGN (aligning to HTML remains
HARDENING for fidelity).

### A5. LOM sidecar (__xid-*.jpg.xml)

| Field | Ours | Real | Class |
| --- | --- | --- | --- |
| identifier | `1_1#/courses/qti_package_maker/probe-figure.jpg` | `23446236_1#/courses/D7.202320/image-1.jpg` | PROVEN-BENIGN |
| structure/namespaces | relation/resource/identifier, imsmd_rootv1p2p1 | identical | match |

Both sidecars are minimal and structurally identical. Our non-matching course
path segment did not prevent ingestion. PROVEN-BENIGN. There are no size or
checksum fields in either sidecar, so payload attachment is not gated on a
declared byte count.

### A6. csfiles/home_dir naming and xid scheme

| Item | Ours | Real | Class |
| --- | --- | --- | --- |
| binary filename | `__xid-1_1.jpg` | `__xid-23446236_1.jpg` | match (pattern) |
| naming contract | `__xid-<resourceId>.jpg`, resourceId `1_1` | `__xid-<resourceId>.jpg`, resourceId `23446236_1` | match |
| xid numbering | minted low int | server PkId range | COSMETIC (value) |
| extension casing | `.jpg` lower | `.jpg` lower | match |
| home_dir path | `csfiles/home_dir/` | same | match |
| payload | valid 1x1 JPEG, 633 B | valid 1280x853 JPEG | see Primary finding |

The `__xid-<resourceId>.jpg` naming contract binds the binary to the
CSResourceLinks `resourceId` and the LOM sidecar id; our chain is internally
consistent (`1_1` throughout) and the payload attached and served. The only
substantive difference is image dimensions.

### A7. res00001.dat CourseSettings

| Field | Ours | Real | Class |
| --- | --- | --- | --- |
| COURSE id attr | absent | `_365518_1` | PROVEN-BENIGN |
| ULTRASTATUS | `C` | `C` | match |

### A8. res00005.dat CSResourceLinks

| Field | Ours | Real | Class |
| --- | --- | --- | --- |
| parentId | `_3439912762_1` (matches item asi id) | `_23221280_1` (matches item asi id) | match (today's fix) |
| courseId | `_1_1` | `_365518_1` | PROVEN-BENIGN |
| resourceId | `1_1` plain | `23446240_1` in CDATA | COSMETIC |
| storageType/aiState | plain | CDATA | COSMETIC |
| link id | `_1_1` | distinct PkId | COSMETIC |

The `parentId` -> item `bbmd_asi_object_id` cross-reference is the fix that
enabled the content-store record; it is intact. The mismatched `courseId` did
not block ingestion. PROVEN-BENIGN.

## Pair B: Learn Classic qti21 (imsqti_item_xmlv2p1)

Not URL-resolved. Probe image is 1x1, so the same false-negative likely
applies. Wiring is structurally very close to the real export. The deltas below
remain UNTESTED-CANDIDATE until a visible-figure re-import.

### B1. imsmanifest.xml

| Surface | Ours | Real | Class |
| --- | --- | --- | --- |
| root identifier | `main manifest` (space) | `man00001` | UNTESTED-CANDIDATE |
| organizations | absent | `<organizations/>` present | UNTESTED-CANDIDATE |
| imsmd prefix binding | -> imsmd_v1p2 | -> LOM (ltsc) | HARDENING |
| extra namespaces | lom, imsmd | csm, imsmd(LOM), imsqti | COSMETIC |
| metadata block | full imsmd:lom | schema/schemaversion only | COSMETIC |
| image resource | `ccres00001` webcontent -> `probe-figure.jpg` root | `ccresNNNNN` webcontent -> `image-N.jpg` root | match (shape) |
| item -> image dependency | present (`ccres00001`) | present | match |
| item -> test dependency | item depends on `assessment_meta` (extra) | test depends on items only | UNTESTED-CANDIDATE |
| dependency direction | item<->meta cycle | test->item->image acyclic | UNTESTED-CANDIDATE |
| item file naming | `qti21_items/item_00001.xml` | `qti21/assessmentItem00001.xml` | COSMETIC |
| web_content log | absent | `qti21/web_content00001.log` | COSMETIC |

The `<img>` webcontent dependency wiring matches. The residual suspects are the
whitespace-bearing root identifier (not a legal IMS/xs:ID) and the missing
`<organizations/>`, either of which can make an importer skip the resource
graph while still parsing question XML.

### B2. Item XML body (img src)

| Surface | Ours | Real | Class |
| --- | --- | --- | --- |
| img src form | `../probe-figure.jpg` | `../image-1.jpg` | match (shape) |
| img tag | `<img .../>` self-closed | `<img ...><br>&#xa0;</img>` | COSMETIC |
| bbmd metadata in item | none | none | match |
| extra outcomeDeclarations | SCORE only | SCORE/FEEDBACKBASIC/MAXSCORE | COSMETIC |

## Pair C: Ultra qti21 (imsqti_item_xmlv2p1 + READ_ONLY/embedded)

Not URL-resolved. Probe image is 1x1, so the Ultra "blank/broken box" may
simply be the invisible 1x1 image rendered in the editor. However, there is one
genuine structural inconsistency that is a real UNTESTED-CANDIDATE for FP1 and
should be corrected before the next round. No `csfiles/` or `externalFiles_*/`
sidecar dirs exist in the real Ultra export; the only media surface is
`READ_ONLY/question/_<id>_1/embedded/`, which ours reproduces.

### C1. imsmanifest.xml

| Surface | Ours | Real | Class |
| --- | --- | --- | --- |
| root identifier | `man00001` | `man00001` | match |
| namespaces / organizations / metadata | identical | identical | match |
| image resource type | `webcontent` | `webcontent` | match |
| image resource href | `READ_ONLY/question/_90000001_1/embedded/image-1.jpg` | `READ_ONLY/question/_23221289_1/embedded/image-N.jpg` | match (shape) |
| item -> image dependency | present (`ccres00001`) | present | match |
| web_content log | absent | present | COSMETIC |

The Ultra manifest is essentially identical in every media-relevant attribute.

### C2. Item identifier vs embedded-folder id contract (key untested candidate)

| Item | `identifier` | Embedded folder | identifier minus `QUE_` | Consistent? |
| --- | --- | --- | --- | --- |
| Real item00001 | `QUE__23221289_1` | `_23221289_1` | `_23221289_1` | YES |
| Real item00002 | `QUE__23221290_1` | `_23221290_1` | `_23221290_1` | YES |
| Ours img/ahref | `QUE_90000001_1` | `_90000001_1` | `90000001_1` | NO |

Class: UNTESTED-CANDIDATE (FP1).

The real contract: item identifier is `QUE_` + the question persistence id,
where that id already begins with an underscore (`_23221289_1`), yielding a
double underscore (`QUE__23221289_1`); the embedded directory uses the same
`_23221289_1`. Ours mints `90000001_1` with no leading underscore, builds
`QUE_90000001_1` (single underscore), but names the folder `_90000001_1`
(leading underscore). Stripping `QUE_` gives `90000001_1`, which does not equal
the folder `_90000001_1`. If Ultra derives the embedded-file storage key from
the item identifier, our embedded files are orphaned and never ingested.
This is worth fixing regardless of the 1x1-asset confound, because it is a real
internal inconsistency the real export never has.

### C3. Item body reference form

| Surface | Ours img | Ours ahref | Real | Class |
| --- | --- | --- | --- | --- |
| reference element | `<img src="../READ_ONLY/.../image-1.jpg" alt="image-1.jpg"/>` | `<a href="../READ_ONLY/.../image-1.jpg">` | `<a href="../READ_ONLY/.../image-N.jpg">` | ahref matches; img differs |
| path shape | `../READ_ONLY/question/_<id>_1/embedded/...` | same | same | match |
| bbmd metadata | none | none | none | match |

Real Ultra represents embedded images as `<a href>` file links, not `<img>`.
The ahref probe reproduces the real body form exactly.

## Root-cause ranking and discriminating experiments

### bb_export (RESOLVED)

Ingestion and linking are confirmed working. The only remaining action is the
probe asset. No package delta needs changing to make images load.

1. Rebuild the probe with a visibly sized figure (e.g. 1280x853). Re-import and
   confirm the image is visible. This is the definitive test; the 633-byte 1x1
   asset was the false negative.
2. Optional HARDENING: add the package-local embed (manifest `<file>` child +
   `res00002/<hash>/image.jpg` + `matapplication`) and switch the body to
   `type="HTML"` to match the real export byte-for-byte. Not required for
   function.

### Learn Classic qti21 (UNTESTED)

Re-run with a visible figure first; the 1x1 asset likely explains the report.
If images are still not visible after that, test in this order:

1. Change the root manifest `identifier` from `main manifest` to `man00001`
   (remove the space; it is not a legal IMS/xs:ID), re-zip, re-import.
2. Insert an empty `<organizations/>` before `<resources>`, re-import.
3. Break the item<->meta dependency cycle: keep only test->item and
   item->image, re-import.

### Ultra qti21 (UNTESTED)

Re-run with a visible figure first. Independently, fix C2 because it is a real
inconsistency:

1. Align the embedded-folder id with the item identifier. Either mint the
   identifier as `QUE__90000001_1` (double underscore, so identifier-minus-QUE_
   equals the `_90000001_1` folder), or rename the folder to `90000001_1` and
   update the manifest href and body `src`. Re-import each variant; whichever
   renders confirms which side Ultra keys on.
2. Add the `web_content00001.log` webcontent resource + file to match the real
   export (low confidence), re-import.
3. If only the ahref probe renders and the img probe does not after C2 is
   fixed, the `<img>` vs `<a href>` element choice matters; adopt `<a href>` to
   match the real Ultra body form.

## Delta counts by classification

| Classification | Count |
| --- | --- |
| PROVEN-BENIGN (bb_export, ingestion confirmed) | 7 |
| UNTESTED-CANDIDATE | 5 |
| HARDENING | 4 |
| COSMETIC | 26 |
| Match (no delta) | many |

PROVEN-BENIGN: A2 course.id, A4 SMART_TEXT, A5 LOM course path, A7 COURSE id,
A8 courseId, plus the CS naming/chain shown to serve bytes (A6, A8 parentId
match). UNTESTED-CANDIDATE: B1 root identifier space, B1 missing organizations,
B1 dependency cycle, C2 id contract, C3 img-vs-ahref. HARDENING: A1 pool
`<file>` child, A1 companion dir, A4 matapplication, B1 imsmd binding.

The single highest-value remaining action is rebuilding probes with a visible
figure; the single highest-value structural fix still worth making is the Ultra
C2 identifier/folder id consistency.
</content>
