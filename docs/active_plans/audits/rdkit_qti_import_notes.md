# Temporary RDKit/QTI Import Notes

Date: 2026-02-07

Purpose: reminder to investigate platform behavior for script-heavy question stems.

Observed behavior:
- Canvas QTI 1.2 import: standard HTML renders, but RDKit JavaScript does not execute.
- Blackboard QTI 2.1 import: HTML renders, but script content can be escaped/broken.
- Blackboard BBQ text import: HTML and RDKit JavaScript both work.
- Blackboard export of BBQ-authored pool to QTI 2.1 can damage script content (escaped tags and broken JS operators).
- ADAPT QTI 1.2 import with script tags: question statement did not load.

Follow-up:
- Re-test with minimal reproducible examples per platform.
- Document supported/unsupported active-content behavior in engine docs.
