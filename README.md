# QTI Package Maker

Converts question banks between learning-management-system formats, so instructors can move
assessments between Blackboard, Canvas, and Moodle without rebuilding them. Embedded images are
now bundled into the exported packages.

The tool reads a question bank in one format and writes it out to many others. Supported targets
include Blackboard (Original and Ultra), Canvas, Moodle Aiken, text2qti, a human-readable text
export, a standalone HTML self-test page, and a print-oriented exam YAML. Seven question types are
supported: multiple choice, multiple answer, matching, numerical entry, fill-in-the-blank,
multi-part fill-in-the-blank, and ordered list.

Image support is now end to end: a Blackboard question-upload text file with `<img>` tags converts
into Canvas and Blackboard packages with the images bundled inside, so figures survive the move
between systems.

<!-- screenshots:begin (managed by screenshot-docs) -->
![Self-test page with multiple choice, multiple answer, and numeric entry questions and an embedded bar chart figure](docs/screenshots/html_selftest_quiz.png)

![Multiple choice question graded as correct, showing the embedded figure and the green CORRECT feedback pill](docs/screenshots/html_selftest_graded.png)

The standalone HTML self-test export renders varied question types with bundled images and instant self-grading feedback.
<!-- screenshots:end -->

## Documentation

Getting started:
- [docs/INSTALL.md](docs/INSTALL.md): Setup, dependencies, and environment.
- [docs/USAGE.md](docs/USAGE.md): CLI usage and worked examples.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): Common issues and fixes.

Formats and engines:
- [docs/FORMATS.md](docs/FORMATS.md): Input and output formats.
- [docs/ENGINES.md](docs/ENGINES.md): Reader and writer engines and their capabilities.
- [docs/QUESTION_TYPES.md](docs/QUESTION_TYPES.md): The seven question types and their fields.

Internals:
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md): Reader/writer engine design and data flow.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md): Repository layout and file map.
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): Developer workflows and testing.

## Quick start

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r pip_requirements.txt
pip install -e .
python3 tools/bbq_converter.py -i bbq-mycourse-questions.txt --all
```

Substitute your own Blackboard question-upload text file, named per the
`bbq-<name>-questions.txt` pattern, for `bbq-mycourse-questions.txt`. Pick specific output engines
with `-f`, for example `-f canvas_qti_v1_2 -f human_readable`. For the BBQ input format, the full
engine list, and more examples, see [docs/USAGE.md](docs/USAGE.md).

## License

Code is licensed under LGPLv3. See [LICENSE.LGPL_v3](LICENSE.LGPL_v3).

## Author

Neil Voss, [bsky.app/profile/neilvosslab.bsky.social](https://bsky.app/profile/neilvosslab.bsky.social).

## Support and links

- **Bitcoin:** [Donate with Bitcoin](bitcoin:bc1qdexkqwzyet93ret40akqmms2jv99wvsgzdshu8?message=support%20qti_package_maker)
- **Dash:** [Donate with Dash](dash:XdDmwBVecEy9yyXKeD7hScLp7oN8rd4XNV?message=support%20qti_package_maker)
- **Patreon:** [Support on Patreon](https://www.patreon.com/vosslab)
- **Paypal:** [Donate via PayPal](https://paypal.me/vosslab)
- [YouTube](https://www.youtube.com/neilvosslab)
- [GitHub](https://github.com/vosslab)
- [Facebook](https://fb.me/neilvosslab)
- [LinkedIn](https://www.linkedin.com/in/vosslab)
