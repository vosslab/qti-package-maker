# Pytest authoring guide

> This file is vendored. Local changes can and will be overwritten by propagation.

Use this guide after deciding that behavior earns a permanent test under
[PYTEST_STYLE.md](PYTEST_STYLE.md). Prefer fewer, stronger permanent tests, and protect behavior
worth preserving rather than incidental implementation. When in doubt, remove the test.

Temporary tests and one-time checks belong in the ignored `tests/_temp/` subtree. Pytest-suitable
`test_*.py` files participate in `pytest tests/` while work is active. Run heavier temporary checks
explicitly with their appropriate tool. Before completing the plan, promote the tests that deserve
permanent protection and remove the rest.

## Authoring checklist

- [ ] The behavior passed the permanent test checklist in [PYTEST_STYLE.md](PYTEST_STYLE.md).
- [ ] The file is `tests/test_<topic>.py` and its test functions are named `test_*`.
- [ ] The test uses plain `assert`, tabs, complete annotations, and repository import order.
- [ ] Inputs and outcomes are fixed, deterministic, and offline.
- [ ] The test finishes well under one second with a few focused assertions.
- [ ] Setup and inputs are inline and close to the assertion.
- [ ] Test-owned files use `tmp_path`.
- [ ] Assertions express public behavior, invariants, errors, or boundaries.

## Use fixtures deliberately

Inline setup is the default. Use durable shared fixtures for these established needs:

1. Use pytest's `tmp_path` fixture for temporary files and directories.
2. Use the `collect_report` autouse harness for repository hygiene reports.
3. Use an existing repository file when that shipped file's required shape or loader behavior is
   the contract under test.

A committed `tests/fixtures/` directory is shared infrastructure. Add one with explicit human
approval when durable shared data is clearer than inline setup.

## Use the hygiene harness

Use [tests/file_utils.py](../tests/file_utils.py) for a repository-wide hygiene test. It owns file
discovery, scratch exclusions, report naming, report lifecycle, parametrization IDs, and failure
formatting. Its docstrings are the API reference.

```python
REPORT_NAME = file_utils.report_name(__file__)
FILES = file_utils.discover_files(
	extensions=(".sh",),
	test_key="topic_name",
)
VIOLATIONS_BY_FILE: dict[str, list[str]] = {}

@pytest.fixture(scope="module", autouse=True)
def collect_report() -> None:
	file_utils.clear_stale_reports()
	VIOLATIONS_BY_FILE.clear()
	VIOLATIONS_BY_FILE.update(file_utils.collect_file_violations(FILES, check_file))
	lines = file_utils.format_violation_report("Topic violations:", VIOLATIONS_BY_FILE)
	if lines:
		file_utils.write_report_lines(REPORT_NAME, lines)

@pytest.mark.parametrize("path", FILES, ids=file_utils.rel_id)
def test_topic(path: str) -> None:
	rel = file_utils.rel_to_root(path)
	message = file_utils.format_violation_assert_message(
		rel, VIOLATIONS_BY_FILE.get(rel, []), REPORT_NAME
	)
	assert rel not in VIOLATIONS_BY_FILE, message
```

Use `collect_python_violations` when the checker consumes a parsed Python AST and
`collect_file_violations` when it consumes file content. Give each hygiene test the `test_key`
matching its filename stem without `test_`.

The module-scoped fixture scans the full file set before parametrized assertions run. It writes one
complete `report_<topic>.txt` only when violations exist; a clean run removes stale reports.

## Configure hygiene discovery

- Keep universal file discovery and scratch exclusions in `tests/file_utils.py`.
- Put repository-specific exclusions in `tests/conftest.py` under `REPO_HYGIENE_FILTERS`.
- Use `extra_filter` only to select a universal subset for one test.
- Use `tests/source_file_line_limit_overrides.txt` only for individually approved external sources.
- Name the module-level discovered path list `FILES` and use `file_utils.rel_id` for readable cases.

`file_utils.discover_files` returns sorted absolute paths. Checkers and repository filters receive
repository-relative POSIX paths. Pass `repo_root=` only when a `file_utils` regression test uses a
controlled temporary repository.

## Verify a test

Run the focused test, then the complete fast lane:

```bash
source source_me.sh && python3 -m pytest tests/test_<topic>.py -q
source source_me.sh && python3 -m pytest tests/ -q
```

Treat a fresh failure as related to the current work until the diff and failing behavior show
otherwise. Preserve the working tree while investigating.

## Record durable changes

Update the repository changelog for durable changes. Record human preferences in
[HUMAN_GUIDANCE.md](HUMAN_GUIDANCE.md) and settled repository policies in
[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md).
