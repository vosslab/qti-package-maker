# File structure

## Top-level layout
- [AGENTS.md](../AGENTS.md): Repository guidelines and agent workflow rules.
- [README.md](../README.md): Project overview and quick start.
- [LICENSE.LGPL_v3](../LICENSE.LGPL_v3): License terms for the repo.
- [VERSION](../VERSION): Project version synchronized with [pyproject.toml](../pyproject.toml).
- [pyproject.toml](../pyproject.toml): Package metadata and build configuration.
- [pip_requirements.txt](../pip_requirements.txt): Runtime dependencies for local installs.
- [qti_package_maker](../qti_package_maker): Main Python package.
- [tools](../tools): CLI scripts for conversion and utilities.
- [tests](../tests): Unit and integration tests plus lint helpers.
- [docs](.): Documentation set for usage, formats, and development.
- [examples](../examples): Small sample QTI ZIPs for manual validation.
- [devel](../devel): Release and development helper scripts.
- [notes](../notes): Local notes and scratch materials.
- [MANIFEST.in](../MANIFEST.in): Source distribution include rules.
- [source_me.sh](../source_me.sh): Helper to set PYTHONPATH.

## Key subtrees
- [qti_package_maker/assessment_items](../qti_package_maker/assessment_items): Item types,
  validation, and the ItemBank container.
- [qti_package_maker/engines](../qti_package_maker/engines): Engine implementations and
  registry for supported formats.
- [qti_package_maker/common](../qti_package_maker/common): Shared utilities such as text
  cleanup, YAML helpers, and manifests.
- [qti_package_maker/data](../qti_package_maker/data): Packaged data files used at runtime.
- [tests/unit](../tests/unit): Unit tests for core components.
- [tests/integration](../tests/integration): End-to-end and CLI coverage.

## Generated artifacts
- Ignored artifacts include `ascii_compliance.txt`, `pyflakes.txt`, and generated
  `*.html`, `*.zip`, and `*.xml` outputs; see [.gitignore](../.gitignore).

## Documentation map
- All docs live under [docs](.).
- Root-level docs include [README.md](../README.md) and [AGENTS.md](../AGENTS.md).

## Where to add work
- New engines: [qti_package_maker/engines](../qti_package_maker/engines).
- New item types or validation: [qti_package_maker/assessment_items](../qti_package_maker/assessment_items).
- Shared helpers: [qti_package_maker/common](../qti_package_maker/common).
- CLI scripts: [tools](../tools).
- Tests: [tests](../tests).
- Documentation: [docs](.).
