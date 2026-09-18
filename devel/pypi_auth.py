# This file is vendored. Local changes can and will be overwritten by propagation.

"""Resolve PyPI repository endpoints and token configuration."""

# Standard Library
import os
import re
import base64
import difflib
import configparser
import urllib.error
import urllib.parse
import urllib.request

# PIP3 modules
from packaging.utils import canonicalize_name

# local repo modules
import pypi_support


DEFAULT_TESTPYPI_INDEX = "https://test.pypi.org/simple/"
DEFAULT_PYPI_INDEX = "https://pypi.org/simple/"


#============================================
def is_pypi_repo(repo: str) -> bool:
	"""Return whether a repository section targets PyPI.

	Args:
		repo (str): Repository section name from .pypirc.

	Returns:
		bool: True when the section targets production PyPI.
	"""
	# "pypi" or "pypi-projectname" target production; everything else is testpypi
	return repo == "pypi" or repo.startswith("pypi-")

#============================================
def resolve_index_url(repo: str) -> str:
	"""Resolve the package index URL for a repository section.

	Args:
		repo (str): Repository section name from .pypirc.

	Returns:
		str: Production or test package-index URL.
	"""
	if is_pypi_repo(repo):
		return DEFAULT_PYPI_INDEX
	return DEFAULT_TESTPYPI_INDEX

#============================================

def extract_token_project_names(token: str) -> list:
	"""Extract project names from a PyPI token using heuristic decoding.

	PyPI tokens are macaroons with project scope encoded as readable ASCII
	in the binary payload. This decodes the base64 suffix and searches for
	JSON-like project name arrays.

	Args:
		token: The full token string starting with 'pypi-'.

	Returns:
		List of project name strings found, or empty list if none detected.
	"""
	# Strip the "pypi-" prefix and decode the base64 macaroon
	token_suffix = token[5:]
	# Add padding if needed
	padding = 4 - (len(token_suffix) % 4)
	if padding < 4:
		token_suffix += "=" * padding
	decoded = base64.urlsafe_b64decode(token_suffix)
	# Search for JSON-style project name arrays like ["project-name"]
	text = decoded.decode("ascii", errors="replace")
	# Look for patterns like ["project-name"] embedded in the macaroon
	matches = re.findall(r'\["([a-zA-Z0-9_.-]+)"\]', text)
	# Filter out UUIDs (project ID caveats) - keep only human-readable names
	uuid_pattern = re.compile(
		r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
	)
	filtered = [m for m in matches if not uuid_pattern.match(m)]
	return filtered

#============================================
def resolve_pypirc_section(config: configparser.ConfigParser, requested: str) -> str:
	"""Resolve a missing .pypirc section by finding prefix or fuzzy matches.

	If exactly one candidate is found, auto-selects it. If multiple candidates
	exist, prompts the user to choose. If none, fails with guidance.

	Args:
		config: Parsed .pypirc config.
		requested: The requested section name that was not found.

	Returns:
		str: The resolved section name.

	Raises:
		RuntimeError: When no matching section is available.
	"""
	sections = [s for s in config.sections() if s != "distutils"]
	# Try prefix matches first (e.g. "testpypi" matches "testpypi-llm")
	candidates = [s for s in sections if s.startswith(f"{requested}-")]
	# Fall back to fuzzy matching if no prefix matches
	if not candidates:
		candidates = difflib.get_close_matches(requested, sections, n=5, cutoff=0.5)
	if not candidates:
		pypi_support.fail(
			f"Section [{requested}] not found in ~/.pypirc.\n\n"
			f"Add a section for this repository:\n\n"
			f"[{requested}]\n"
			"repository = https://test.pypi.org/legacy/\n"
			"username = __token__\n"
			"password = pypi-YOUR_TOKEN_HERE\n\n"
			"Then add it to [distutils] index-servers."
		)
	# Auto-select if exactly one match
	if len(candidates) == 1:
		pypi_support.print_info(
			f"Section [{requested}] not found. "
			f"Using [{candidates[0]}] instead."
		)
		return candidates[0]
	# Prompt user to choose from multiple matches
	pypi_support.print_warning(f"Section [{requested}] not found in ~/.pypirc.")
	pypi_support.print_info("Available matching sections:")
	for i, name in enumerate(candidates, 1):
		pypi_support.print_info(f"  {i}) {name}")
	while True:
		choice = input("Choose repository number: ").strip()
		if choice.isdigit():
			idx = int(choice)
			if 1 <= idx <= len(candidates):
				selected = candidates[idx - 1]
				pypi_support.print_info(f"Using [{selected}]")
				return selected
		pypi_support.print_info("Invalid choice. Enter a number from the list.")

#============================================
def require_pypirc_token(repo: str, package_name: str) -> tuple:
	"""Validate that ~/.pypirc has a usable token for the target repository.

	Parses ~/.pypirc directly and resolves the section, credentials, and
	repository URL. If the exact section is missing but similar sections
	exist, prompts the user to select one.

	Args:
		repo: The repository section name (e.g., 'testpypi', 'testpypi-llm').
		package_name: The package being uploaded.

	Returns:
		tuple: Resolved repository, username, token, and repository URL.

	Raises:
		RuntimeError: When the configuration or token cannot be used.
	"""
	pypirc_path = os.path.expanduser("~/.pypirc")

	# Check file exists
	if not os.path.isfile(pypirc_path):
		pypi_support.fail(
			"~/.pypirc not found. Create it with your API token:\n\n"
			f"[{repo}]\n"
			"username = __token__\n"
			"password = pypi-YOUR_TOKEN_HERE\n\n"
			"Create tokens at https://test.pypi.org/manage/account/token/ (TestPyPI)\n"
			"or https://pypi.org/manage/account/token/ (PyPI)."
		)

	# Parse the file
	config = configparser.ConfigParser()
	config.read(pypirc_path)

	# Resolve section: exact match, prefix match, or fuzzy match
	if not config.has_section(repo):
		repo = resolve_pypirc_section(config, repo)

	# Read credentials and optional repository URL from the resolved section
	username = config.get(repo, "username", fallback="")
	if not username:
		pypi_support.fail(f"~/.pypirc [{repo}] has no username set.")
	if username != "__token__":
		pypi_support.print_warning(
			f"~/.pypirc [{repo}] username is '{username}', expected '__token__'.\n"
			"Token-based auth requires username = __token__"
		)

	password = config.get(repo, "password", fallback="")
	if not password:
		pypi_support.fail(f"~/.pypirc [{repo}] has no password set. Add your API token.")

	# Optional repository URL override from .pypirc
	repo_url = config.get(repo, "repository", fallback="")

	if not password.startswith("pypi-"):
		pypi_support.print_warning(
			f"~/.pypirc [{repo}] password does not start with 'pypi-'.\n"
			"PyPI API tokens always start with 'pypi-'."
		)
		result = (repo, username, password, repo_url)
		return result

	# Heuristic: check if token is scoped to a different project
	project_names = extract_token_project_names(password)
	if project_names:
		canonical_name = canonicalize_name(package_name)
		canonical_scopes = [canonicalize_name(name) for name in project_names]
		if canonical_name not in canonical_scopes:
			scoped_text = ", ".join(project_names)
			if is_pypi_repo(repo):
				token_url = "https://pypi.org/manage/account/token/"
			else:
				token_url = "https://test.pypi.org/manage/account/token/"
			pypi_support.fail(
				f"~/.pypirc [{repo}] token is scoped to: {scoped_text}\n"
				f"Package '{package_name}' is not in that list.\n"
				f"Upload would fail with 403 Forbidden.\n"
				f"Create a token for '{package_name}' at {token_url}"
			)

	result = (repo, username, password, repo_url)
	return result

#============================================
def require_index_reachable(index_url: str) -> None:
	"""Ensure a package index URL is reachable.

	Args:
		index_url (str): Package-index URL to check.

	Raises:
		RuntimeError: When the URL is invalid or unavailable.
	"""
	# Validate URL scheme to prevent file:// or other dangerous schemes
	parsed = urllib.parse.urlparse(index_url)
	if parsed.scheme not in ('http', 'https'):
		pypi_support.fail(f"Invalid URL scheme (only http/https allowed): {index_url}")

	request = urllib.request.Request(index_url, method="GET")
	try:
		with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310
			if response.status >= 400:
				pypi_support.fail(f"Index URL returned HTTP {response.status}: {index_url}")
	except urllib.error.URLError as exc:
		pypi_support.fail(f"Index URL not reachable: {index_url} ({exc})")
#============================================

DEFAULT_PYPI_UPLOAD = "https://upload.pypi.org/legacy/"
DEFAULT_TESTPYPI_UPLOAD = "https://test.pypi.org/legacy/"
#============================================

def resolve_upload_url(repo: str, pypirc_url: str) -> str:
	"""Resolve the upload URL for twine.

	Uses the repository URL from ~/.pypirc if present, otherwise
	falls back to the default based on the repo section name.

	Args:
		repo: The repository section name.
		pypirc_url: The repository URL from ~/.pypirc (may be empty).

	Returns:
		str: The upload endpoint URL.
	"""
	if pypirc_url:
		return pypirc_url
	if is_pypi_repo(repo):
		return DEFAULT_PYPI_UPLOAD
	return DEFAULT_TESTPYPI_UPLOAD
#============================================
