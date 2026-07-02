# Related projects

This map helps new visitors place qti-package-maker in the assessment-tooling
ecosystem: where its questions come from, which plain-text quiz formats it reads
and writes, and how it compares to other LMS import and QTI converters.

## Confirmed related projects

### biology-problems (bptools)
- Relationship: same-author sibling repo and upstream question source
- Link: https://github.com/vosslab/biology-problems
- Evidence: `qti_package_maker/common/franken_bptools.py` adapts the bptools
  question-generation helpers, and `docs/active_plans/active/image_support_plan.md`
  treats bptools as a downstream caller of the `BaseItem` API.
- Notes: bptools generators emit Blackboard Question Upload (BBQ) text that
  qti-package-maker converts into QTI and other formats; project home is
  https://biologyproblems.org.

### text2qti
- Relationship: optional integration target and bidirectional engine
- Link: https://github.com/gpoore/text2qti
- Evidence: `qti_package_maker/engines/text2qti/` reads and writes the text2qti
  Markdown-based quiz format, and `docs/ENGINES.md` lists text2qti as a read+write
  engine.
- Notes: text2qti creates Canvas-importable QTI zips from plain text; this repo
  interoperates with its format rather than replacing it.

### Blackboard Quiz Generator (Oklahoma Christian)
- Relationship: optional integration target and bidirectional engine
- Link: https://github.com/OklahomaChristian/BlackboardQuizGenerator
- Evidence: the `qti_package_maker/engines/okla_chrst_bqgen/` engine reads and
  writes the Oklahoma Christian bank-generator text format documented in
  `docs/ENGINES.md`.
- Notes: live tool at https://ed.oc.edu/blackboardquizgenerator/ converts Word or
  text quizzes into Blackboard pool zips.

## Possible related projects

### moodle-qformat_canvas
- Relationship: same-domain alternative
- Link: https://github.com/jmvedrine/moodle-qformat_canvas
- Evidence: Moodle question-format plugin that imports Canvas quiz exports; shares
  the cross-LMS question-conversion domain but no direct repo link.
- Confidence: low

### amc2moodle
- Relationship: same-domain alternative
- Link: https://pypi.org/project/amc2moodle/
- Evidence: converts Auto Multiple Choice and LaTeX questions into Moodle XML;
  overlapping question-format conversion purpose, no direct dependency.
- Confidence: low

### moodle-questions
- Relationship: same-domain alternative
- Link: https://github.com/gethvi/moodle-questions
- Evidence: Python library for building and manipulating Moodle question banks;
  parallel domain, independent implementation.
- Confidence: low

### pyAssignment
- Relationship: prior art or inspiration
- Link: https://pypi.org/project/pyassignment/
- Evidence: Python framework for authoring assignments and exporting to formats
  including Blackboard; similar authoring-to-LMS-export goal, no direct link.
- Confidence: low

## Evidence notes

Confirmed entries come from repo code and docs: the `engines/text2qti/` and
`engines/okla_chrst_bqgen/` read+write engines, the `common/franken_bptools.py`
adapter, and the bptools caller references in the image-support plan. The project
homepage in `pyproject.toml` (https://biologyproblems.org) ties this library to
the same-author biology-problems repo. Possible entries are same-domain LMS and
QTI converters carried forward from the prior version of this file with working
links; they share the question-format conversion domain but have no reciprocal
link or dependency evidence.
