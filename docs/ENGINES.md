# Engines

## Output engines

### QTI v1.2 engine (Canvas QTI v1.2)
- **Engine name:** `canvas_qti_v1_2`
- **Format type:** QTI v1.2 (IMS XML format)
- **Compatible LMS:** Canvas, LibreTexts ADAPT
- **File output:** ZIP file containing QTI v1.2 XML files

### QTI v2.1 engine (Blackboard QTI v2.1)
- **Engine name:** `blackboard_qti_v2_1`
- **Format type:** QTI v2.1 (IMS XML format)
- **Compatible LMS:** Blackboard Learn (Original)
- **File output:** ZIP file containing QTI v2.1 XML files

### Blackboard Ultra support (no dedicated engine)
There is no dedicated Ultra-specific writer engine; a dedicated Ultra
engine was removed 2026-07-02 as redundant (see "Decisions and Failures"
in [docs/CHANGELOG.md](CHANGELOG.md)'s 2026-07-02 entry). User field
evidence showed every `blackboard_qti_v2_1` export already imports
cleanly into Ultra, so Ultra is served by two existing engines instead:

- **`blackboard_qti_v2_1`** via Ultra's "Import from QTI 2.1 package": images
  render; matching questions are skipped by Ultra's QTI 2.1 importer; table
  widths, color, and most inline CSS are stripped on import.
- **`blackboard_export_zip`** via Ultra's "Import from file": supports
  matching questions (Ultra's QTI 2.1 path does not); images render.

For the full empirical contract on what Ultra accepts, rewrites, or
destroys on import (retained as historical reference from the removed
engine's development), see
[docs/BLACKBOARD_ULTRA_NOTES.md](BLACKBOARD_ULTRA_NOTES.md).

### Human-readable engine
- **Engine name:** `human_readable`
- **Format type:** Simple text file
- **Compatible LMS:** Any system that supports plain-text import
- **File output:** A structured text file listing the questions and answers
- **Use case:** Review questions before conversion to QTI

### Moodle Aiken engine
- **Engine name:** `moodle_aiken`
- **Format type:** Moodle Aiken plain-text multiple-choice format
- **Compatible LMS:** Moodle (Aiken question import)
- **File output:** A `.txt` file in Aiken format
- **CLI flag:** `-A` or `--aiken`
- **Supported item types:** MC only (all other types are skipped)
- **Use case:** Simple multiple-choice import into Moodle

### Oklahoma CHRST BQGEN engine
- **Engine name:** `okla_chrst_bqgen`
- **Format type:** Plain-text bank-generator format (read and write)
- **Compatible LMS:** N/A (text bank-generator interchange)
- **File output:** A `.txt` file in the okla_chrst_bqgen format
- **Supported item types:** MC, MA, MATCH, FIB (NUM, MULTI_FIB, and ORDER are skipped)

### Blackboard question upload engine
- **Engine name:** `bbq_text_upload`
- **Format type:** Blackboard-specific TXT upload format
- **Compatible LMS:** Blackboard (Original Course View)
- **File output:** A `.txt` file that Blackboard can upload

### HTML self-test engine
- **Engine name:** `html_selftest`
- **Format type:** HTML-based self-assessment
- **Compatible LMS:** Any web-based environment
- **File output:** A self-contained HTML file
- **Use case:** Self-assessment quizzes without LMS integration

### Exam YAML engine
- **Engine name:** `exam_yaml`
- **Format type:** YAML-based print-oriented exam format
- **Compatible LMS:** N/A (used to generate print/ODT exams, not LMS import)
- **File output:** A `.yaml` file with an exam title, date, and question statements
- **Use case:** Print-ready exam generation; write-only, lossy (no answer keys or scoring metadata)

### Blackboard pool export engine
- **Engine name:** `blackboard_export_zip`
- **Format type:** Blackboard pool export ZIP (QTI-1.2-derived envelope with BB extensions)
- **Compatible LMS:** Blackboard Learn (Original)
- **File output:** ZIP file in the Blackboard pool export format
- **CLI flag:** `-B` or `--bbexport`
- **Supported item types:** MC, MA, MATCH, FIB, NUM, MULTI_FIB
- **Unsupported item types:** ORDER (not supported by this format), media attachments
- **Verification:** Generated packages are verified locally by opening the ZIP and confirming
  the presence of `imsmanifest.xml` and pool data files. Live Blackboard import relies on the
  working hypothesis that the importer does not hard-validate `.bb-package-sig`; the engine
  omits this signature file because it is computed server-side on genuine Blackboard exports.
- **Key differences from QTI v2.1 engines:**
  - Uses QTI 1.2 XML structure wrapped in Blackboard-specific extensions
  - Produces the seven-file `.dat` sidecar layout expected by Blackboard pool import
  - No `.bb-package-sig` file is written

#### Known limitations

- Re-importing MC/MA items whose choices carry a strippable label prefix can yield a new
  internal content hash, so exact-ID matching may drift. The root cause is that the item
  content hash is computed before the choice-prefix stripper runs. Question and answer
  content still round-trips correctly; an internal hashing fix is tracked separately.
- A live Blackboard/Ultra import is an optional out-of-band acceptance step. The engine omits
  `.bb-package-sig` because it is server-computed and not reproducible from package contents;
  CI does not perform a live import, so import success is unverified.

## Engine capabilities

### Read and write

| Engine name              | Can read   | Can write   |
|--------------------------|------------|-------------|
| bbq_text_upload          | yes        | yes         |
| blackboard_export_zip    | yes        | yes         |
| blackboard_qti_v2_1      | X          | yes         |
| canvas_qti_v1_2          | X          | yes         |
| exam_yaml                | X          | yes         |
| html_selftest            | X          | yes         |
| human_readable           | X          | yes         |
| moodle_aiken             | X          | yes         |
| okla_chrst_bqgen         | yes        | yes         |
| text2qti                 | yes        | yes         |

### Assessment item types

| Item type   | bbq text upload   | blackboard export zip   | blackboard qti v2.1   | canvas qti v1.2   | exam yaml   | html selftest   | human readable   | moodle aiken   | okla chrst bqgen   | text2qti   |
|-------------|-------------------|-------------------------|-----------------------|-------------------|-------------|-----------------|------------------|----------------|--------------------|------------|
| FIB         | yes               | yes                     | yes                   | X                 | yes         | yes            | yes              | X              | yes                | yes        |
| MA          | yes               | yes                     | yes                   | yes               | yes         | yes            | yes              | X              | yes                | yes        |
| MATCH       | yes               | yes                     | yes                   | yes               | yes         | yes            | yes              | X              | yes                | no         |
| MC          | yes               | yes                     | yes                   | yes               | yes         | yes            | yes              | yes            | yes                | yes        |
| MULTI_FIB   | yes               | yes                     | yes                   | yes               | yes         | yes            | yes              | X              | X                  | no         |
| NUM         | yes               | yes                     | yes                   | yes               | yes         | yes            | yes              | X              | X                  | yes        |
| ORDER       | yes               | X                       | yes                   | X                 | yes         | yes            | yes              | X              | X                  | no         |

## Media and image support

Item content keeps the author's plain `<img src="images/foo.jpg" alt="...">`;
there is no `asset:` scheme stored in an item. Each engine declares one media
policy value and every referenced image routes through exactly one of four
outcomes. The shared media layer lives in
`qti_package_maker/common/media_assets.py`; see
[ENGINE_AUTHORING.md](ENGINE_AUTHORING.md) for the authoring contract.

### Media policy values

| Policy | Meaning |
| --- | --- |
| **package** | Image bytes are copied into the output package and referenced from item HTML. |
| **reference_warn** | Item content keeps a working reference to the image; one itemized warning is emitted per referenced image so the user knows to supply the file. |
| **placeholder_warn** | The format has no image channel, so each `<img>` becomes a readable `[image: name.ext]` placeholder plus one itemized warning. |
| **fail** | Any referenced image raises `MediaPolicyError`. No shipped engine uses this default; it is available for strict pipelines. |

First-class raster types are PNG, JPEG, and GIF. SVG is packaged but warned;
any other extension (for example `.webp`) raises. External URLs and data URIs
are never bundled by a packaging engine; the `media_assets.apply_media_policy`
call is the single channel that emits the external, data-uri, and SVG warnings, so every engine
surfaces them identically. The three file-packaging engines
(`canvas_qti_v1_2`, `blackboard_qti_v2_1`, `blackboard_export_zip`) raise
`MediaPolicyError` on a `data:` URI.

### Per-engine media behavior

| Engine name | Media policy | Behavior |
| --- | --- | --- |
| `canvas_qti_v1_2` | **package** | Images packaged under `media/`; item `<img src>` uses a selectable token (relative default, or `$IMS-CC-FILEBASE$` for gate A). |
| `blackboard_qti_v2_1` | **package** | Images packaged at the QTI 2.1 root; `<img src>` uses the `../` form matching the Blackboard sample export. |
| `blackboard_export_zip` | **package** | Images embedded via the Blackboard csfiles mechanism (binary + LOM sidecar, `res00005.dat` CSResourceLinks, `@X@` body token); write to read roundtrip preserves bytes and references. |
| `html_selftest` | **package** | Images inlined as base64 `data:` URIs, so the single HTML file has zero external references (mkdocs-material fragment safe at any nav depth). |
| `text2qti` | **reference_warn** | Local images copied into a `media/` folder beside the output and `<img>` rewritten to markdown `![alt](media/name.png)`; external and data-uri references kept verbatim with a warning. |
| `bbq_text_upload` | **reference_warn** | `<img>` kept verbatim in the upload text; one itemized warning per image reminds the user to upload the file manually. |
| `exam_yaml` | **reference_warn** | `<img>` written verbatim into the YAML statement with a warning. |
| `human_readable` | **reference_warn** | Pre-render description substitution (name, alt, source) because the pretty-printer strips all tags; one warning per image. |
| `moodle_aiken` | **placeholder_warn** | Aiken plain text has no image markup; `<img>` replaced with a `[image: name.ext]` placeholder plus one warning per image. |
| `okla_chrst_bqgen` | **placeholder_warn** | Plain-text format with no image markup; `<img>` replaced with a `[image: name.ext]` placeholder plus one warning per image. |

### Support-claim status

- The `blackboard_qti_v2_1` and `blackboard_export_zip` packaging paths are
  evidenced directly from committed Blackboard sample exports and proven by an
  in-code write to read roundtrip.
- Canvas Classic Quizzes rendering of packaged images ships on the plan's
  documented fallback: the spec-relative `<img src>` variant is the default
  and is unverified on a live Canvas import. Gate A's sandbox probe is
  blocked (Instructure discontinued the Free for Teacher program); the
  `$IMS-CC-FILEBASE$` variant stays available via the engine's
  `canvas_src_variant` constructor kwarg for anyone with institutional
  Canvas access to run the probe later.
- Blackboard Ultra has no dedicated writer engine; images reach Ultra
  through `blackboard_qti_v2_1` ("Import from QTI 2.1 package") and
  `blackboard_export_zip` ("Import from file"). Gate D's final
  visible-figure probe round (2026-07-02) confirmed packaged images render
  on import through both paths, so no placeholder policy or separate Ultra
  engine is needed. The probe kits and manual import steps are in
  [MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md); each kit's ZIP layout and
  manifest shape is already proven by an automated fixture.
