# PYTEST_STYLE.md

> This file is vendored. Local changes can and will be overwritten by propagation.

Language Model guide to Neil pytest policy.

## Permanent test policy

Prefer fewer, stronger permanent tests. Each test should protect behavior worth preserving without
unnecessarily constraining future design.

Treat tests as liabilities as well as assets. A permanent test adds confidence, maintenance cost,
and a constraint on future implementations. It can preserve undesirable behavior as effectively as
desirable behavior, so every permanent test must earn its place.

- Protect intentionally stable behavior that is important and plausibly subject to regression.
- Test externally meaningful contracts, domain invariants, security boundaries, data integrity,
  and deliberate product decisions.
- Prefer adaptability over speculative edge-case coverage. Add an edge case when it represents an
  actual requirement, demonstrated risk, or recurring failure.
- Ground requirements and gates in product behavior, correctness, security, repository policy,
  measured constraints, or demonstrated failures.
- Give each new blocking CI, build, release, or repository-wide behavior gate a failure plan. State
  what failure means and the decision, correction, or recovery that follows.
- Use temporary verification for implementation proof. Promote only the checks that deserve lasting
  protection.
- When in doubt, remove the test.

## Permanent test checklist

Answer these questions before adding or retaining a permanent test:

- [ ] Names the regression it prevents and why that regression matters.
- [ ] Protects intentionally stable, meaningful behavior worth preserving.
- [ ] Covers a plausible regression not already protected clearly.
- [ ] Grounds its precision and edge cases in an actual need.
- [ ] Includes an actionable failure plan when it creates a new blocking gate.
- [ ] Provides more lasting value than a temporary implementation check.

Use `tests/_temp/` while the case for permanent coverage is unclear.

## Temporary verification

Use the ignored `tests/_temp/` subtree for temporary tests, reproductions, exploratory checks, and
one-time implementation proof. Pytest-suitable temporary tests named `test_*.py` participate in the
normal `pytest tests/` run while work is active; `tests/conftest.py` does not exclude this subtree.
Run heavier temporary checks from `tests/_temp/` explicitly with their appropriate tool.

Before completing the plan, review every plan-specific check in `tests/_temp/`. Promote a check
when its behavior earns permanent protection and remove the rest. Plan closeout is the cleanup
mechanism; `tests/_temp/` is a workspace, not a permanent test tier.

## Test lanes

- `tests/test_*.py` contains permanent, fast pytest unit and integration tests.
- `tests/_temp/` contains ignored, temporary verification. Pytest collects suitable `test_*.py`
  files; heavier checks run explicitly.
- `tests/e2e/` contains permanent non-browser whole-system tests run explicitly.
- `tests/playwright/` contains permanent browser tests run with Playwright.
- `tests/test_*.mjs` contains permanent Node tests when a repository uses that lane.

Pytest excludes only `tests/e2e/` and `tests/playwright/` through `tests/conftest.py`. See
[E2E_TESTS.md](E2E_TESTS.md) for permanent whole-system tests and
[PYTEST_AUTHORING_GUIDE.md](PYTEST_AUTHORING_GUIDE.md) for pytest construction.

## Reliable permanent pytest

- Use fixed inputs and deterministic outcomes.
- Keep the fast lane offline and well under one second per test.
- Keep setup and inputs inline and close to the behavior under test.
- Use `tmp_path` for test-owned files.
- Use a few focused assertions that express the meaningful result.
- Move reusable test mechanics into small helpers with their own clear contract.
- Use `tests/e2e/` or `tests/playwright/` when real processes, services, browsers, networks, or
  whole-system workflows are essential to the behavior.

`tests/test_checkout_disk_budget.py` is the documented exception to the no-subprocess fast-lane
default. Its local `du` call measures the checkout that the gate protects.

## Assertion shapes

Prefer assertions that survive refactoring:

- Fixed input produces the required output.
- Encode then decode preserves the value.
- A domain invariant remains true.
- Invalid input produces the required error.
- A security or architecture boundary remains enforced.
- A relative or range property holds without pinning a tunable value.

```python
assert parse_title_year("The.Matrix.1999.BluRay.mkv") == ("The Matrix", "1999")

encoded = encode(value)
assert decode(encoded) == value

assert 0.0 <= score <= 1.0
assert score_exact_match > score_different_title
```

A fragile pytest couples success to transient context or incidental structure, such as current
dates, inventory sizes, internal name lists, tunable defaults, external fixture state, real-time
delays, or unseeded randomness. Assert those details only when they are actual requirements.

## Failure triage

- Treat a fresh failure as related to the current work until evidence shows otherwise.
- Inspect the working-tree diff and the failing behavior before classifying it as pre-existing.
- Preserve the working tree while investigating; use read-only comparisons instead of stashing.
- Follow the gate's failure plan when a blocking gate fails.
