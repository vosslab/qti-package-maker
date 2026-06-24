# Blackboard export zip forgeability audit (M0)

Audit date: 2026-06-23. Samples read from `BB_Export_ZIP/` under repo root.

## Minimal required file set

Every sample pool directory contains exactly these top-level files:

| File | Type | Required |
| --- | --- | --- |
| `imsmanifest.xml` | XML content package manifest | YES |
| `res00001.dat` | `course/x-bb-coursesetting` (96 bytes, nearly empty) | YES |
| `res00002.dat` | `assessment/x-bb-qti-pool` -- the pool XML | YES |
| `res00003.dat` | `course/x-bb-courseassessmentcreationsettings` | YES (present in all samples) |
| `res00004.dat` | `course/x-bb-rubrics` (55 bytes, `<LEARNRUBRICS/>`) | YES (present in all samples) |
| `res00005.dat` | `course/x-bb-csresourcelinks` | YES (present in all samples) |
| `res00006.dat` | `course/x-bb-stdsalignments` | YES (present in all samples) |
| `res00007.dat` | `course/x-bb-crsrubricassocation` (67 bytes, `<COURSERUBRICASSOCIATIONS/>`) | YES (present in all samples) |
| `.bb-package-info` | Plain-text property file (Learn server metadata) | YES |
| `.bb-log-info` | Plain-text export log | YES |
| `.bb-package-sig` | 32-byte MD5 hex string | **NO -- omit (see sig finding below)** |
| `csfiles/` | Empty directory (appears in all samples) | Include empty dir |
| `res00001/` | Empty directory (sidecar for res00001.dat) | Include empty dir |

The pool XML is always `res00002.dat`. The pool type `assessment/x-bb-qti-pool` is
identified by the `type=` attribute in the manifest resource element, not by filename.

## Sig finding: server-side, non-reproducible -- engine omits it

`.bb-package-sig` is a 32-character uppercase hex string (MD5-shaped).
The `.bb-package-info` file includes `app.release.number`, `cx.config.course.id`, and
Learn server path metadata stamped at export time. Candidate MD5s of the manifest,
the pool `.dat`, and the concatenated `.dat` files all fail to reproduce the sig.
The sig is computed server-side and cannot be regenerated from package contents alone.

**Engine policy: write NO `.bb-package-sig`.** A present-but-non-server sig is more
likely to be rejected on import than an absent one. The working hypothesis -- that
Blackboard import does not hard-validate the sig -- is supported by the fact that
`Import Pool / Import from file` is a first-class operation and users cannot
regenerate a server sig after export. An optional out-of-band import confirms this
hypothesis but gates no milestone.

## Serialization notes

- Pool dat (`res00002.dat`): Blackboard's serialization is inconsistent.
  Some samples are minified (single long line, no trailing newline).
  Some samples are pretty-printed. The engine emits its own clean serialization;
  byte-for-byte faithfulness is not required.
- `imsmanifest.xml`: all observed samples are minified (one or a few lines).
- Encoding: all files are UTF-8 as declared.
- The `bb:` namespace prefix is `http://www.blackboard.com/content-packaging/` in the manifest.

## Per-type verification table

Values extracted from real sample bytes. Columns are read directly from the pool XML files.

| Internal type | bbmd_questiontype element value | response element | fibtype | respcond count | has correct+incorrect titles | <and> of <or> nesting | RIGHT_MATCH_BLOCK |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MC | `Multiple Choice` | `response_lid` | n/a | 7 (1 correct + 1 incorrect + N per-choice) | YES | no | no |
| MATCH | `Matching` | `response_lid` (one per prompt) | n/a | N+1 (N NO_TITLE + 1 incorrect) | partial (incorrect only) | no | YES (flow class) |
| FIB | `Fill in the Blank` | `response_str` ident=`response` | `String` | N accepted + 1 incorrect | YES (incorrect branch) | no | no |
| NUM | `Numeric` | `response_num` ident=`response` | `Decimal` | 2 (1 correct + 1 incorrect) | YES | no | no |
| MULTI_FIB | `Fill in the Blank Plus` | `response_str` (one per blank) | `String` | 2 (1 correct + 1 incorrect) | YES | YES | no |

Notes per type:

**MC (`Multiple Choice`)**
- `respcond_count` = 2 named (title=`correct`, title=`incorrect`) + one per choice option (title absent/`NO_TITLE`).
  The per-choice branches carry the choice ident (without a value attribute) and set SCORE=0.
  A minimum clean structure requires at least `correct` and `incorrect` branches.
- `varequal respident='response'` in the correct branch points to the correct choice label ident.
- The incorrect branch uses `<other/>` as its conditionvar child.

**MATCH (`Matching`)**
- One `response_lid` per prompt in `presentation`, each containing `render_choice` with
  `flow_label` elements listing the answer options.
- `RIGHT_MATCH_BLOCK` appears as `flow class="RIGHT_MATCH_BLOCK"` in `presentation` (not a tag name).
  It lists the right-side text (answers pool) as `flow class="Block"` > `flow class="FORMATTED_TEXT_BLOCK"` > `material` > `mat_extension` > `mat_formattedtext type="SMART_TEXT"`.
- `respcondition` branches: one `NO_TITLE` branch per prompt (each contains a `varequal` keying
  prompt ident -> correct answer label ident) plus one final `title="incorrect"` branch with `<other/>`.
- No `title="correct"` branch observed; scoring is per-prompt via the `NO_TITLE` branches.

**FIB (`Fill in the Blank`)**
- Single `response_str ident="response"` + `render_fib fibtype="String"`.
- Each accepted answer is a separate `respcondition` with title=UUID (not `correct`).
  Each carries `varequal respident="response" case="No"` with the accepted answer text.
- Final branch: `title="incorrect"` with `<other/>` and `setvar SCORE=0`.
- `case="No"` means case-insensitive matching.

**NUM (`Numeric`)**
- `response_num ident="response"` + `render_fib fibtype="Decimal"`.
- Correct respcondition: title=UUID (not `correct`). conditionvar contains:
  `<vargte respident="response">answer-tolerance</vargte>`,
  `<varlte respident="response">answer+tolerance</varlte>`,
  `<varequal respident="response" case="No">exact_answer</varequal>` -- all siblings
  directly under `conditionvar` (no `<and>` wrapper).
- Final branch: `title="incorrect"` with `<other/>` and `setvar SCORE=0`.
- Two respconditions total.

**MULTI_FIB (`Fill in the Blank Plus`)**
- One `response_str` per blank, each with its own `ident` key (the blank label, e.g. `MR`, `MY`).
  All have `render_fib fibtype="String"`.
- Correct respcondition: `title="correct"`. conditionvar contains `<and>` wrapping one `<or>` per blank.
  Each `<or>` holds one or more `<varequal respident="KEY" case="No">answer</varequal>` elements
  (one per accepted spelling for that blank).
- Incorrect branch: `title="incorrect"` with `<other/>` and `setvar SCORE=0`.
- `qmd_absolutescore_max` = number of blanks (as a decimal string, e.g. `4.000000000000000`).
- The `incorrect` branch IS present and IS required for a clean structure (confirmed in both
  MULTI_FIB samples: `Ch05.3` and `Ch05.4`).

## Known sample directories

Samples used for this audit (all under `BB_Export_ZIP/` at repo root):

| Sample directory | Types found |
| --- | --- |
| `Pool_ExportFile_E4.202620_Ch03b_General_MC_Full` | MC |
| `Pool_ExportFile_E4.202620_Ch01_Bond_Types_Match4_python` | MATCH |
| `Pool_ExportFile_GC.202610_Ch02.4_Overhang_Sequence_FiB` | FIB |
| `Pool_ExportFile_E4.202620_Ch03a_Peptide_Side_Chain_2aa_FIB` | FIB |
| `Pool_ExportFile_E4.202620_Ch05_Gel_Migration_Calc_Numeric` | NUM |
| `Pool_ExportFile_GC.202610_Ch05.3_Three-Point_Test_Cross_xDistances_Plus_2025` | MULTI_FIB |
| `Pool_ExportFile_GC.202610_Ch05.4_Unordered_Tetrad_xThree_Gene_Distance_Plus_2024` | MULTI_FIB |

No MA sample is available in `BB_Export_ZIP/`. MA type knowledge comes from the plan context
and is not directly confirmed by a sample at M0. The plan notes MA uses `rcardinality="Multiple"`
on `response_lid`.

## Probe tool and samples (removed)

The raw `BB_Export_ZIP/` sample pools and the throwaway `devel/bb_rezip_probe.py` probe used
during M0 are not committed and have been removed. The per-type verification table above is the
durable record of what they showed. Engine coverage now relies on the self-contained in-code
round-trip (`tests/integration/test_blackboard_export_zip_roundtrip.py`), which builds one item
of every type, writes it through the engine, and reads it back, depending on no external samples.
