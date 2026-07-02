# News

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
