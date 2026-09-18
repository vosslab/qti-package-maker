# News

## v26.09 - 2026-09-18

### Highlights

- Blackboard Ultra no longer has to lose table-cell drawings. Opt-in
  `--html-to-image` screenshots gels, restriction maps, and agglutination
  wells to packaged PNGs on `-2` (QTI 2.1) and `-B` (pool export).
- Live Ultra import of a 99-item paternity-gel pool confirmed the figures
  render after upload.
- RDKit JavaScript canvases can be redrawn the same way; that path is
  available but is not required for the DNA-profiling and restriction-map
  generators.

### Upgrade notes

- New runtime dependencies: pip `playwright` and `rdkit`. For drawing
  conversion, also run `playwright install chromium`.
- `--html-to-image` is off by default and applies only to the two Blackboard
  packaging engines. Mixed CLI runs leave other formats unchanged.
- The npm Playwright/TypeScript toolchain is not used; Chromium comes from
  the pip Playwright package.

## v26.07 - 2026-07-02

### Highlights

- Blackboard image support is now proven on real servers: figures render after
  import into both Blackboard Ultra and Learn Classic on every import path.
  Earlier "image lost" reports were a false alarm caused by an invisible
  1x1-pixel test figure.
- Two real Blackboard import bugs are fixed: Learn now accepts the marked
  correct answer on multiple choice and multiple answer QTI 2.1 items, and
  pool exports no longer drop their embedded images.
- A new package integrity checker (`devel/check_package_integrity.py`)
  inspects any package ZIP before upload and flags dangling references,
  mismatched answer ids, invisible tiny images, and unsafe identifiers.
- The documentation set was overhauled: a rewritten `README.md` with
  screenshots, a new [COOKBOOK.md](COOKBOOK.md) of verified recipes, and
  refreshed usage, install, and troubleshooting guides.

### Upgrade notes

- The `bb_ultra_qti_v2_1` engine and its `-u`/`--ultra` CLI flag are removed.
  For Blackboard Ultra, use `-2` (`blackboard_qti_v2_1`) or `-B`
  (`blackboard_export_zip`); both are field-verified to import into Ultra.

## v26.06 - 2026-07-02

### Highlights

- Questions with images now carry their pictures all the way through. Every
  export engine handles `<img>` content and packages, references, or describes
  it in the form each target expects, so figures survive the trip into Canvas,
  Blackboard, Moodle, LibreTexts ADAPT, and the standalone self-test HTML.
- You pick how images travel: package the file, reference it, drop in a text
  placeholder, or fail loudly. Each engine documents its own default behavior.
- New Blackboard pool-export engine reads and writes Blackboard's native "Pool"
  package format, available from the command line with the `-B` flag.
- The self-test HTML got a visual refresh: rounded feedback pills, larger
  tap-friendly answer controls, and dark-mode support.

### Upgrade notes

- Regenerate any cached `html_selftest` self-test fragments from the 26.03
  release. The self-test output changed with the 26.06 bump, so older cached
  fragments are stale.
