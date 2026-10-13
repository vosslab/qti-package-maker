# Human guidance

- 2026-10-12: Validate inline CSS strictly, like unmatched HTML tags. Reject confirmed errors
  with actionable messages; BP must correct its generators. Never silently repair CSS or turn
  confirmed errors into warnings. Accept CSS that cannot reliably be classified as invalid.
- 2026-10-12: Prefer existing parsers and validators for common colors, dimensions, property
  names, and values. Keep Python and Rust behavior consistent; avoid obscure CSS edge cases.
- 2026-10-12: QPM abbreviates QTI Package Maker. Keep the established `qti_package_maker`
  Python import namespace and distribution; use QPM for Rust, Wasm, and project integration names.
  Use direct arguments, functions, or defaults instead of custom environment configuration.

<!-- VENDORED HEADER: START -->
Record the durable guidance Neil Voss states, or approves for preservation here, in his own words:
first person or close paraphrase, one to three lines per bullet. Material he supplies as a source
may inform [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) once it is settled, and an entry of uncertain
origin belongs there too. Rules: [REPO_STYLE.md](REPO_STYLE.md).
[PROPAGATED HEADER - ENTRIES BELOW ARE YOURS]
<!-- VENDORED HEADER: END -->

## Decision priority

## Review expectations

## Working style

- I normally use Graphify update or fresh, sometimes context, and now the published map. Keep this
  command line to those recurring actions, with Ollama available when my Claude usage is maxed out.
- Let one Graphify run update or rebuild the data and publish `docs/GRAPHIFY.md` with its compact
  community SVG. Never put the full per-symbol export under `docs/`.
- Let Markdown link checks include newly created, nonignored untracked files for their first 24
  hours. Keep ignored files unavailable.
