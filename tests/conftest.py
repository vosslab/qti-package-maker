# Exclude both end-to-end tiers from pytest collection. tests/playwright/
# holds browser-driven tests (Playwright), and tests/e2e/ holds heavier
# shell/Python whole-system runners. Both run outside pytest -- see
# docs/PLAYWRIGHT_USAGE.md and docs/E2E_TESTS.md.
collect_ignore = ["e2e", "playwright"]

# Standard Library
import os
import subprocess
import sys

# Pip3 Library
import pytest


REPO_ROOT = subprocess.check_output(
	["git", "rev-parse", "--show-toplevel"],
	text=True,
).strip()
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
if TESTS_DIR not in sys.path:
	sys.path.insert(0, TESTS_DIR)
if REPO_ROOT not in sys.path:
	sys.path.insert(0, REPO_ROOT)


@pytest.fixture
def sample_items():
	return {
		"MC": ("What is your favorite color?", ["blue", "red", "yellow"], "blue"),
		"MA": (
			"Which are types of fruit?",
			["orange", "banana", "apple", "lettuce", "spinach"],
			["orange", "banana", "apple"],
		),
		"MATCH": ("Match item to color.", ["orange", "banana", "lettuce"], ["orange", "yellow", "green"]),
		"NUM": ("What is 2 + 2?", 4.0, 0.1, True),
		"FIB": ("Complete the sentence: The sky is __.", ["blue"]),
		"MULTI_FIB": ("Fill in the blanks: A [1] is a [2].", {"1": ["dog"], "2": ["mammal"]}),
		"ORDER": ("Arrange the planets by size.", ["Mercury", "Mars", "Venus", "Earth"]),
	}


@pytest.fixture
def sample_bbq_lines():
	return [
		"MC\t2+2?\t3\tincorrect\t4\tcorrect",
		"MA\tPrime numbers?\t2\tcorrect\t3\tcorrect\t4\tincorrect\t5\tcorrect",
		"MAT\tMatch capital to country.\tUSA\tWashington\tFrance\tParis",
		"NUM\tApprox pi?\t3.14\t0.01",
		"FIB\tCapital of France?\tParis",
		"FIB_PLUS\tFill in: [animal] has milk.\tanimal\tcow",
		"ORD\tOrder these.\tOne\tTwo\tThree",
	]


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
	monkeypatch.chdir(tmp_path)
	return tmp_path

# REPO_HYGIENE_FILTERS is the repo-local hygiene-exclusion registry (Layer 2).
# file_utils.discover_files reads it from this conftest, which is the right
# home because propagation only merges the collect_ignore block above into this
# file; the rest of conftest survives and may differ per repo. Vendored files
# (file_utils.py and every tests/test_*.py) get overwritten by propagation,
# so they must hold no repo-specific data. Put repo-specific exclusions here.
#
# Shape and rules:
#   - It is a dict: key -> list of repo-relative POSIX glob patterns.
#   - Keys are "all" or a vendored test key. A test key is the test filename
#     stem with the leading "test_" removed (test_pyflakes_code_lint.py ->
#     "pyflakes_code_lint", test_ascii_compliance.py -> "ascii_compliance").
#   - Patterns match repo-relative POSIX paths via fnmatch.fnmatchcase
#     (case-sensitive). A match excludes the file from that test.
#   - "all" patterns apply to every test; a test-key list applies only when
#     that test_key is passed to discover_files.
#   - Recursive directory exclusions need an explicit /** because fnmatch's *
#     does not cross "/". Use "temp_scripts/**" to exclude a whole subtree.
#
# This template has no repo-specific exclusions, so the registry is empty.
# Example entries (commented out; this repo needs none):
#   REPO_HYGIENE_FILTERS = {
#       "all": ["temp_scripts/**", "TEMPLATE.py"],
#       "ascii_compliance": ["human_readable-*.html"],
#       "pyflakes_code_lint": ["devel/scratch_*.py"],
#   }
REPO_HYGIENE_FILTERS = {}

# === OPTIONAL_HELPERS_MENU ===
# See meta/docs/PROPAGATION_RULES.md for the managed-block propagation contract.
# This block is an optional helpers menu appended once by propagation and
# never overwritten on subsequent propagation runs. Uncomment a recipe below
# to enable it for this repo. Every line here is a comment by default so an
# untouched consumer behaves exactly as it did before propagation added this
# block.
#
# Note: inserting the repo root onto sys.path is now done unconditionally at the
# top of this file via file_utils.get_repo_root(), so it is no longer a recipe.
#
# --- Recipe 1: redirect matplotlib config dir to a per-repo tmp location ---
# Prevents matplotlib from writing to the home-directory config cache during
# tests, which can cause cross-repo pollution or permission errors in CI.
# Set MPLCONFIGDIR to a writable tmp path before matplotlib is imported.
# Note: PYTHONUNBUFFERED and PYTHONDONTWRITEBYTECODE are handled by
# source_me.sh and belong there, not here.
#
#	import os
#	import tempfile
#	os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mpl_"))
