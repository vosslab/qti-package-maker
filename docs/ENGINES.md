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

### QTI v2.1 engine (Blackboard Ultra QTI v2.1)
- **Engine name:** `bb_ultra_qti_v2_1`
- **Format type:** QTI v2.1 (IMS XML format)
- **Compatible LMS:** Blackboard Ultra
- **File output:** ZIP file containing QTI v2.1 XML files
- **CLI flag:** `-u` or `--ultra`
- **Supported item types:** MC, MA, FIB, NUM, MULTI_FIB, MATCH
- **Unsupported item types:** ORDER (silently dropped by Ultra importer)
- **Key differences from Learn engine:**
  - Strict HTML sanitization: strips `style=`, `class=`, all CSS blocks, and deprecated table attributes
  - Heading levels are rewritten downward by Ultra on import
  - Column widths cannot be controlled; auto-layout only
  - Underline (`<u>`) becomes empty `<span>`
  - No inline image support through standard QTI paths
  - Hot Spot questions are not round-trip stable
  - Tables with tabular data (kinetics, gel migrations) render correctly after HTML serialization fix
  - Tables used for layout or graphics (e.g., chemistry diagrams) do not survive Ultra's restrictions
- **For full empirical contract and limitations, see:** [docs/BLACKBOARD_ULTRA_NOTES.md](BLACKBOARD_ULTRA_NOTES.md)

### Human-readable engine
- **Engine name:** `human_readable`
- **Format type:** Simple text file
- **Compatible LMS:** Any system that supports plain-text import
- **File output:** A structured text file listing the questions and answers
- **Use case:** Review questions before conversion to QTI

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
| bb_ultra_qti_v2_1        | X          | yes         |
| bbq_text_upload          | yes        | yes         |
| blackboard_export_zip    | yes        | yes         |
| blackboard_qti_v2_1      | X          | yes         |
| canvas_qti_v1_2          | X          | yes         |
| html_selftest            | X          | yes         |
| human_readable           | X          | yes         |
| text2qti                 | yes        | yes         |

### Assessment item types

| Item type   | bb ultra qti v2.1   | bbq text upload   | blackboard export zip   | blackboard qti v2.1   | canvas qti v1.2   | html selftest   | human readable   | text2qti   |
|-------------|---------------------|-------------------|-------------------------|-----------------------|-------------------|-----------------|------------------|------------|
| FIB         | yes                 | yes               | yes                     | yes                   | X                 | yes            | yes              | yes        |
| MA          | yes                 | yes               | yes                     | yes                   | yes               | yes            | yes              | yes        |
| MATCH       | yes                 | yes               | yes                     | yes                   | yes               | yes            | yes              | no         |
| MC          | yes                 | yes               | yes                     | yes                   | yes               | yes            | yes              | yes        |
| MULTI_FIB   | yes                 | yes               | yes                     | yes                   | yes               | yes            | yes              | no         |
| NUM         | yes                 | yes               | yes                     | yes                   | yes               | yes            | yes              | yes        |
| ORDER       | X                   | yes               | X                       | yes                   | X                 | yes            | yes              | no         |
