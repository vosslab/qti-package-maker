# Install

qti_package_maker runs as an importable Python package and through the scripts
under [tools/](../tools/). "Installed" means either the package is importable on
your `PYTHONPATH` (the no-install path via `source_me.sh`) or it is pip-installed
into your environment.

## Requirements

- Python 3.10+ for the package; development and tests target Python 3.12.
- Python 3.11+ for development scripts that use the standard-library `tomllib` module.
- pip, and Git for source installs.
- Runtime dependencies: `crcmod`, `lxml`, `num2words`, `pyyaml`, `tabulate`
  (installed automatically by the pip steps below).

## Quick start (no install)

Run directly from a checkout without installing the package. `source_me.sh` adds
the repo root to `PYTHONPATH` for the current shell.

```sh
git clone https://github.com/vosslab/qti_package_maker.git
cd qti_package_maker
pip install -r pip_requirements.txt
source source_me.sh
python3 tools/bbq_converter.py -h
```

## Install from source

```sh
git clone https://github.com/vosslab/qti_package_maker.git
cd qti_package_maker
python3 -m venv .venv
source .venv/bin/activate
pip install -r pip_requirements.txt
pip install -e .
```

## Install from PyPI

```sh
python3 -m pip install qti-package-maker
bbq_converter.py -h
```

The PyPI package installs the educator-facing converter command:

```text
bbq_converter.py
```

## Verify install

```sh
bbq_converter.py -h
```

This prints the converter help, confirming that the package and its educator-facing
command are installed. The engine table provides a deeper verification:

```sh
python3 -m qti_package_maker.engines.engine_registration
```

## Troubleshooting

- `VERSION MISMATCH` from `tools/bbq_converter.py`: the installed package version
  differs from the repo `VERSION` file. Run `pip install -e .` from the repo root
  to resync, as the message instructs.

## Known gaps

- Confirm supported operating systems beyond macOS if needed.
- Confirm whether published PyPI releases track this repo's release cadence.
