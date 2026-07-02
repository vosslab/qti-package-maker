# Roadmap

Priorities organized by time horizon. Dates are directional, not commitments.

## Near term (0-3 months)
- Image/media support has landed across every engine (shared `media_assets`
  API, four-value `media_policy`, image packaging for Canvas, Blackboard QTI
  2.1, and Blackboard Original). The only open work is human sandbox
  verification: import the Canvas gate A and Blackboard Ultra gate D probe
  kits and record results in [docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md).
- Decide the Blackboard Ultra packaged-image upgrade after gate D: Ultra
  currently ships `[image: name.ext]` placeholder text, and the real-package
  render verdict waits on the sandbox import.
- Engine selection fix: exact match, unique prefix, else error listing candidates.
- Auto-detect reader selection in QTIPackageInterface (zip/xml/txt heuristics).
- Quiet mode that suppresses warnings and progress output.
- Deterministic shuffle option (seeded) for BBQ and HTML selftest writers.
- CRC collision tracking and warning report with item details.
- Expand unit tests for readers and writers (BBQ, text2qti, QTI manifest).
- Normalize text cleanup in one helper (strip &nbsp;, collapse whitespace, CRC prefix trim).
- Reader validation: required field counts with line numbers in errors.
- Centralized warnings helper with consistent formatting and test coverage.
- Ensure HTML validation fails clearly when lxml is missing.
- Keep engine capability tables in sync with the registry.

## Mid term (3-9 months)
- Hints and feedback data model: hints list, correct/incorrect feedback, choice feedback.
- Text format syntax for hints/feedback (BBQ and text2qti) plus round-trip tests.
- QTI 1.2 and 2.1 feedback mapping with predictable fallbacks.
- HTML selftest hint toggle and feedback blocks in UI.
- Stable choice identifiers for per-choice feedback across formats.
- Optional item metadata (points, tags, learning objectives, difficulty).
- Reader support for QTI 1.2 and 2.1 packages where feasible.
- Compatibility checks before writes to surface unsupported item types early.

## Longer term (9-18 months)
- New import formats (JSON/YAML) with schema and validation.
- Stable choice IDs in the item model to support per-choice feedback safely.
- Cross-engine compatibility checks to preflight unsupported item types.
- Performance pass for large banks (streamed reads, memory limits, profiling).
- Schema validation for generated QTI XML using xmlschema.
- Plugin style engine discovery with explicit versioning and capability metadata.
- Bulk conversion CLI for batch inputs with summary reports.

## Out of scope
- Canvas QTI 1.2 ORDER items (Canvas does not support them).
- HOTSPOT image items on write: no HOTSPOT item type exists in the item model,
  so `blackboard_export_zip` reads hotspot images but does not author them.
- Rasterization preprocessing (HTML tables or JS figures to PNG): deferred to a
  future standalone tool rather than folded into this package.
- LMS-specific UI features beyond standard QTI outputs.
- Online validation services or network-dependent conversions.
- Native LMS API integrations (gradebook sync, user provisioning).
- Hosted web UI or SaaS service for conversions.

## Legacy detail (retained)

## Hints across formats

### Goal
Support multiple, separate hints per item across all formats with predictable
fallbacks when a format has limited hint support.

### Behavior notes
- QTI 2.1 hints cannot be hidden; they are always available to the learner and
  are commonly rendered as a hint button in LMS interfaces.
- The common request to "ask for a hint instead of submitting an answer" can be
  modeled in QTI 2.1 using the `endAttemptInteraction` path.
- Non-QTI formats should surface hints consistently (for example, a toggle or
  a hint block), even if the underlying format has no formal hint element.

### Plan
1. Add `hints: list[str]` to assessment item data (default `[]`).
2. Validate each hint string as HTML-safe content.
3. Define a stable hint syntax for text-based formats (BBQ/text2qti).
4. Writers:
   - QTI 1.2: map hints to item feedback or the closest available structure.
   - QTI 2.1: map hints to modal feedback / interaction-linked feedback; always
     visible as per spec.
   - HTML self-test: add a hint toggle per item.
   - Human-readable: render a labeled hint block.
5. Readers:
   - Parse hints when present and store them in `hints`.
6. Add smoke tests for round-tripping items with multiple hints.

### References
- QTI 2.1 spec: [1EdTech QTI 2.1](https://www.1edtech.org/standards/qti/index#QTI21)
- QTI 1.2 spec: [1EdTech QTI 1.2](https://www.1edtech.org/standards/qti/index#QTI%201.2)
- QTI 2.1 hint path: [endAttemptInteraction element](https://www.imsglobal.org/question/qtiv2p1/imsqti_infov2p1.html#element10402)

### Risks
- Hints in QTI 2.1 cannot be hidden; some LMS UI behavior may differ.
- Text formats may lose hint granularity unless a strict syntax is enforced.

### Open questions
- Should hints affect CRC / uniqueness of items?
- Should hints include optional "cost" or scoring metadata?
- Preferred hint syntax for BBQ and text2qti inputs?

## Feedback across formats

### Goal
Support overall feedback plus per-choice/distractor feedback with predictable
fallbacks when a format cannot represent all feedback types.

### Plan
1. Add optional feedback fields to item data:
   - `feedback_correct` and `feedback_incorrect`.
   - `choice_feedback` for MC/MA (keyed by choice text or a stable choice id).
2. Validate feedback strings for HTML safety and minimum content.
3. Define a stable feedback syntax for text-based formats (BBQ/text2qti).
4. Writers:
   - QTI 1.2: map to `itemfeedback` and `respcondition` where available.
   - QTI 2.1: map to `modalFeedback` and response processing outcomes.
   - HTML self-test: render per-choice and overall feedback in the UI.
   - Human-readable: render labeled feedback blocks.
5. Readers:
   - Parse per-choice feedback when present and store it in the item model.
6. Add smoke tests that round-trip per-choice feedback for MC/MA.

### Risks
- Some formats/LMSes may ignore per-choice feedback.
- Choice text keys can break if choices are transformed; consider stable IDs.
- Mixed feedback types need a clear precedence rule.

### Open questions
- Should feedback keys be stable IDs rather than choice text?
- Should per-choice feedback apply per selection in MA or as a combined response?

## HTML selftest theming

### Goal
Ensure `html_selftest` output supports light and dark modes when embedded in
MkDocs Material.

### Status
Implemented in the html_selftest theme injection (2025-12-29).

### Plan
1. Add CSS variables for colors and spacing in the generated HTML.
2. Map variables to MkDocs Material palette tokens (default/slate) such as
   `--md-default-bg-color`, `--md-default-fg-color`, `--md-primary-fg-color`,
   and `--md-accent-fg-color`.
3. Provide a fallback `prefers-color-scheme` theme for standalone use.

### Risks
- Theme token names may change across MkDocs Material versions.
