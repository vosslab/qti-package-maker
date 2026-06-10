# QTI Package Maker

A Python package and CLI that converts Blackboard Question Upload (BBQ) text files into QTI
packages and other formats (Canvas, Blackboard, human-readable text, HTML self-tests). For
instructors and developers moving assessments across LMSs.

## Documentation
Core docs:
- [docs/INSTALL.md](docs/INSTALL.md): Setup and dependencies.
- [docs/USAGE.md](docs/USAGE.md): CLI usage and examples.
- [docs/FORMATS.md](docs/FORMATS.md): Input/output formats and engine list.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): Common issues and fixes.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md): System design overview.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md): Repo layout and file map.

More docs:
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): Developer workflows and testing.
- [docs/CHANGELOG.md](docs/CHANGELOG.md): Change history.

## Quick start
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r pip_requirements.txt
pip install -e .
python3 tools/bbq_converter.py -i bbq-example-questions.txt -1
```

Input files must follow the `bbq-<name>-questions.txt` naming pattern. For the BBQ format and
more examples, see [docs/USAGE.md](docs/USAGE.md).
