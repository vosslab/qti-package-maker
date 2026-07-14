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
pip install qti-package-maker
```

## Verify install

```sh
python3 -m qti_package_maker.engines.engine_registration
```

This prints the registered engine table (read/write and media-policy columns),
confirming the package imports and its engines load. An import-only check also
works:

```sh
python3 -c "import qti_package_maker; print(qti_package_maker.__name__)"
```

## Troubleshooting

- `VERSION MISMATCH` from `tools/bbq_converter.py`: the installed package version
  differs from the repo `VERSION` file. Run `pip install -e .` from the repo root
  to resync, as the message instructs.

## Known gaps

- Confirm supported operating systems beyond macOS if needed.
- Confirm whether published PyPI releases track this repo's release cadence.
