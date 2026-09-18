#!/usr/bin/env python3
# This file is vendored. Local changes can and will be overwritten by propagation.


# Standard Library
import os
import re
import sys
import shutil
import pathlib
import tomllib
import argparse
import tempfile
import subprocess
import datetime
import time

# local repo modules
import pypi_auth
import pypi_support
import version_lib

# PIP3 modules
from packaging.utils import canonicalize_name
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

TESTPYPI_PROJECT_BASE = "https://test.pypi.org/project/"
PYPI_PROJECT_BASE = "https://pypi.org/project/"
BUILD_LOG_NAME = "build_output.log"
TEST_INSTALL_RETRIES = 6
TEST_INSTALL_RETRY_DELAY = 10


def parse_args() -> argparse.Namespace:
	"""Parse command line arguments.

	Returns:
		The parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Build and upload a Python package to PyPI or TestPyPI.",
	)

	repo_group = parser.add_argument_group("repository")
	mode_group = repo_group.add_mutually_exclusive_group()
	mode_group.add_argument(
		'-t', '--test', dest='use_main', action='store_false',
		help='Upload to TestPyPI (default).',
	)
	mode_group.add_argument(
		'-m', '--main', dest='use_main', action='store_true',
		help='Upload to production PyPI.',
	)
	repo_group.add_argument(
		'-r', '--repo', dest='repo_override', default='',
		help='Override: use a specific ~/.pypirc section name.',
	)
	parser.set_defaults(use_main=False)

	behavior_group = parser.add_argument_group("behavior")
	behavior_group.add_argument(
		"--version-check",
		dest="check_only",
		help="Check if the version exists on the index and exit.",
		action="store_true",
	)

	behavior_group.add_argument(
		"--build-only",
		dest="build_only",
		help="Run all build steps but skip upload and test install.",
		action="store_true",
	)
	behavior_group.add_argument(
		"--verbose",
		dest="verbose_upload",
		help="Show verbose Twine output during upload.",
		action="store_true",
	)

	behavior_group.add_argument(
		"--set-version",
		dest="set_version",
		help="Update VERSION and pyproject.toml, then tag and push.",
		default="",
	)

	args = parser.parse_args()
	return args

#============================================

def resolve_repo_root() -> str:
	"""Resolve the repository root through Git."""
	result = pypi_support.run_command_allow_fail(
		["git", "rev-parse", "--show-toplevel"],
		os.getcwd(),
		True,
	)
	if result.returncode != 0 or not result.stdout.strip():
		pypi_support.fail("Unable to resolve the Git repository root.")
	repo_root = pathlib.Path(result.stdout.strip())
	pyproject_path = repo_root / "pyproject.toml"
	if not pyproject_path.is_file():
		pypi_support.fail(f"pyproject.toml not found at repo root: {pyproject_path}")
	return str(repo_root)

#============================================

def resolve_pyproject_path(project_dir: str) -> str:
	"""Resolve and validate the pyproject.toml path."""
	path_value = os.path.join(project_dir, "pyproject.toml")
	if not os.path.isfile(path_value):
		pypi_support.fail(f"pyproject.toml not found: {path_value}")
	return path_value

#============================================

def read_pyproject(pyproject_path: str) -> dict:
	"""Load pyproject.toml into a dict.

	Args:
		pyproject_path: Path to pyproject.toml.

	Returns:
		The parsed pyproject data.
	"""
	with open(pyproject_path, "rb") as handle:
		data = tomllib.load(handle)
	return data

#============================================

def extract_project_metadata(pyproject_data: dict) -> tuple[str | None, str | None]:
	"""Extract package name and version from pyproject data.

	Args:
		pyproject_data: Parsed pyproject data.

	Returns:
		A tuple of (name, version) when available.
	"""
	name: str | None = None
	version: str | None = None

	project_data = pyproject_data.get("project", {})
	if project_data:
		name_value = project_data.get("name")
		version_value = project_data.get("version")
		if name_value:
			name = str(name_value)
		if version_value:
			version = str(version_value)

	if name or version:
		result = (name, version)
		return result

	tool_data = pyproject_data.get("tool", {})
	poetry_data = tool_data.get("poetry", {})
	if poetry_data:
		name_value = poetry_data.get("name")
		version_value = poetry_data.get("version")
		if name_value:
			name = str(name_value)
		if version_value:
			version = str(version_value)

	result = (name, version)
	return result

#============================================

def resolve_package_name(metadata_name: str | None) -> str:
	"""Resolve the package name from pyproject metadata."""
	name = metadata_name or ""
	if not name:
		pypi_support.fail("Package name not found in pyproject.toml.")
	return name

#============================================

def resolve_version(metadata_version: str | None) -> str:
	"""Resolve the package version from pyproject metadata."""
	version = metadata_version or ""
	if not version:
		pypi_support.fail("Package version not found in pyproject.toml.")
	return version

#============================================

def resolve_import_name(arg_value: str, package_name: str) -> str:
	"""Resolve the import name for the test import.

	Args:
		arg_value: Value from arguments.
		package_name: The package name.

	Returns:
		The resolved import name.
	"""
	import_name = arg_value.strip() if arg_value else ""
	if not import_name:
		import_name = re.sub(r"[-.]", "_", package_name)
	return import_name


def validate_version_string(version: str) -> None:
	"""Validate that the version string parses as PEP 440."""
	try:
		Version(version)
	except InvalidVersion as exc:
		pypi_support.fail(f"Invalid version string: {version} ({exc})")


def normalize_version_string(version: str) -> str:
	"""Return the normalized PEP 440 version string."""
	return str(Version(version))


def read_requires_python(pyproject_data: dict) -> str:
	"""Read the requires-python field from pyproject data."""
	project_data = pyproject_data.get("project", {})
	requires_python = project_data.get("requires-python", "")
	return str(requires_python).strip()


def require_python_version(requires_python: str) -> None:
	"""Ensure the running Python satisfies requires-python."""
	if not requires_python:
		pypi_support.print_warning("No requires-python specified in pyproject.toml; skipping check.")
		return
	specifier = SpecifierSet(requires_python)
	current_version = Version(
		f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
	)
	if current_version not in specifier:
		pypi_support.fail(
			"Python version does not satisfy requires-python: "
			f"{current_version} not in {requires_python}"
		)


def require_git_clean(project_dir: str) -> None:
	"""Ensure the git working tree has no staged or unstaged changes."""
	result = pypi_support.run_command_allow_fail(
		["git", "status", "--porcelain", "--untracked-files=no"],
		project_dir,
		True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to check git status. Is git installed?")
	status = result.stdout.strip()
	if status:
		lines = status.splitlines()
		sample = "\n".join(lines[:5])
		pypi_support.fail(
			"Working tree has tracked changes. Commit or stash before release.\n"
			f"{sample}"
		)


def require_main_branch(project_dir: str) -> None:
	"""Ensure the release is on the main branch."""
	result = pypi_support.run_command_allow_fail(
		["git", "rev-parse", "--abbrev-ref", "HEAD"],
		project_dir,
		True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to determine current git branch.")
	branch = result.stdout.strip()
	if branch != "main":
		pypi_support.fail(f"Release must be cut from main. Current branch: {branch}")


def require_version_tag(project_dir: str, version: str) -> None:
	"""Ensure the git tag for the version exists."""
	tag_name = f"v{version}"
	result = pypi_support.run_command_allow_fail(
		["git", "tag", "--list", tag_name],
		project_dir,
		True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to check git tags.")
	if not result.stdout.strip():
		pypi_support.fail(
			"Missing version tag. Create it with:\n"
			f"git tag -a {tag_name} -m \"Release {tag_name}\"\n"
			f"git push origin {tag_name}"
		)


def require_twine_available(python_exe: str, project_dir: str) -> None:
	"""Ensure twine is installed and runnable."""
	result = pypi_support.run_command_allow_fail([python_exe, "-m", "twine", "--version"], project_dir, True)
	if result.returncode != 0:
		pypi_support.fail("twine is not available. Install it with: python -m pip install twine")


def require_dist_empty(project_dir: str) -> None:
	"""Ensure dist/ is empty after cleaning."""
	dist_dir = os.path.join(project_dir, "dist")
	if not os.path.isdir(dist_dir):
		return
	entries = [name for name in os.listdir(dist_dir) if not name.startswith(".")]
	if entries:
		joined = ", ".join(sorted(entries))
		pypi_support.fail(f"dist/ is not empty after cleaning: {joined}")


def require_editable_install_in_sync(
	python_exe: str, project_dir: str, package_name: str, version: str
) -> None:
	"""Ensure the editable install version matches the repo version.

	An editable install (pip install -e .) caches metadata at install time.
	When the version is bumped in pyproject.toml without re-running pip install,
	the installed metadata goes stale and version checks in tools will fail.

	Args:
		python_exe: Python executable.
		project_dir: Project directory.
		package_name: Package name to check.
		version: Expected version from pyproject.toml.
	"""
	import_name = re.sub(r"[-.]", "_", package_name)
	# Check if the package is importable at all
	check_cmd = [python_exe, "-c", f"import {import_name}"]
	result = pypi_support.run_command_allow_fail(check_cmd, project_dir, True)
	if result.returncode != 0:
		# Not installed, nothing to check
		return
	# Get the installed version via importlib.metadata
	version_cmd = [
		python_exe, "-c",
		f"import importlib.metadata; print(importlib.metadata.version('{package_name}'))",
	]
	result = pypi_support.run_command_allow_fail(version_cmd, project_dir, True)
	if result.returncode != 0:
		return
	installed_version = result.stdout.strip()
	repo_normalized = str(Version(version))
	installed_normalized = str(Version(installed_version))
	if repo_normalized != installed_normalized:
		pypi_support.fail(
			f"Editable install is stale: installed {package_name} is {installed_version}, "
			f"but pyproject.toml says {version}.\n"
			f"Run 'pip install -e .' from {project_dir} to sync."
		)

#============================================

def require_pytest_passes_if_available(python_exe: str, project_dir: str) -> None:
	"""Run pytest if it is installed."""
	result = pypi_support.run_command_allow_fail([python_exe, "-c", "import pytest"], project_dir, False)
	if result.returncode != 0:
		pypi_support.print_warning("pytest not installed; skipping tests.")
		return
	pypi_support.print_step("Running pytest...")
	pypi_support.run_command([python_exe, "-m", "pytest", "-q"], project_dir, False)


def require_up_to_date_with_origin_main(project_dir: str) -> None:
	"""Ensure local main is synced with origin/main."""
	fetch_result = pypi_support.run_command_allow_fail(
		["git", "fetch", "origin", "main"],
		project_dir,
		True,
	)
	if fetch_result.returncode != 0:
		pypi_support.fail("Unable to fetch origin/main for sync check.")
	result = pypi_support.run_command_allow_fail(
		["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"],
		project_dir,
		True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to compare HEAD with origin/main.")
	parts = result.stdout.strip().split()
	if len(parts) != 2:
		pypi_support.fail("Unexpected rev-list output when comparing to origin/main.")
	ahead = int(parts[0])
	behind = int(parts[1])
	if ahead == 0 and behind == 0:
		return
	if ahead > 0 and behind == 0:
		pypi_support.fail(
			"Local main has commits not pushed to origin/main. "
			"Run: git push origin main"
		)
	if behind > 0 and ahead == 0:
		pypi_support.fail(
			"Local main is behind origin/main. "
			"Run: git pull --ff-only origin main"
		)
	pypi_support.fail(
		"Local main has diverged from origin/main. "
		"Run: git pull --rebase origin main"
	)


def update_version_files(project_dir: str, version: str) -> None:
	"""Update VERSION and pyproject.toml with the new version."""
	version_path = os.path.join(project_dir, "VERSION")
	current_version = ""
	if os.path.isfile(version_path):
		with open(version_path, "r") as handle:
			current_version = handle.read().strip()
	if current_version != version:
		with open(version_path, "w") as handle:
			handle.write(f"{version}\n")

	pyproject_path = resolve_pyproject_path(project_dir)
	with open(pyproject_path, "r") as handle:
		contents = handle.read()
	updated, changed = version_lib.update_pyproject(
		contents,
		["project", "tool.poetry"],
		version,
	)
	if not changed:
		pypi_support.fail("Unable to update version in pyproject.toml.")
	if updated != contents:
		with open(pyproject_path, "w") as handle:
			handle.write(updated)


def has_tracked_changes(project_dir: str) -> bool:
	"""Return True if git has tracked changes."""
	result = pypi_support.run_command_allow_fail(
		["git", "status", "--porcelain", "--untracked-files=no"],
		project_dir,
		True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to check git status.")
	return bool(result.stdout.strip())


def commit_version_bump(project_dir: str, version: str) -> bool:
	"""Commit the version bump if there are tracked changes."""
	pypi_support.run_command(["git", "add", "VERSION", "pyproject.toml"], project_dir, False)
	if not has_tracked_changes(project_dir):
		pypi_support.print_warning("Version files already match; skipping commit.")
		return False
	pypi_support.run_command(["git", "commit", "-m", f"Bump version to {version}"], project_dir, False)
	return True


def tag_and_push_version(project_dir: str, version: str, push_main: bool) -> None:
	"""Tag and push the version."""
	tag_name = f"v{version}"
	tag_result = pypi_support.run_command_allow_fail(
		["git", "tag", "--list", tag_name],
		project_dir,
		True,
	)
	if tag_result.returncode != 0:
		pypi_support.fail("Unable to check git tags.")
	if not tag_result.stdout.strip():
		pypi_support.run_command(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], project_dir, False)
	if push_main:
		pypi_support.run_command(["git", "push", "origin", "main"], project_dir, False)
	pypi_support.run_command(["git", "push", "origin", tag_name], project_dir, False)

#============================================

def format_bytes(size_bytes: int) -> str:
	"""Format byte counts for human-readable output.

	Args:
		size_bytes: Size in bytes.

	Returns:
		The formatted size.
	"""
	size = float(size_bytes)
	units = ["B", "KB", "MB", "GB"]
	unit_index = 0
	while size >= 1024.0 and unit_index < len(units) - 1:
		size = size / 1024.0
		unit_index += 1
	formatted = f"{size:.1f} {units[unit_index]}"
	return formatted

#============================================

def list_dist_files(dist_dir: str) -> list[pathlib.Path]:
	"""List distribution files in dist/.

	Args:
		dist_dir: Path to dist/.

	Returns:
		List of dist file paths.
	"""
	dist_path = pathlib.Path(dist_dir)
	if not dist_path.exists():
		return []
	files = sorted([path for path in dist_path.iterdir() if path.is_file()])
	return files

#============================================

def show_dist_files(dist_dir: str) -> None:
	"""Print dist files with sizes.

	Args:
		dist_dir: Path to dist/.
	"""
	files = list_dist_files(dist_dir)
	if not files:
		pypi_support.print_warning("No distribution files found in dist/.")
		return
	for path in files:
		size_text = format_bytes(path.stat().st_size)
		pypi_support.print_info(f"dist/{path.name} ({size_text})")

#============================================

def clean_build_artifacts(project_dir: str) -> None:
	"""Remove build, dist, and egg-info artifacts.

	Args:
		project_dir: Project directory.
	"""
	paths = ["build", "dist"]
	for name in paths:
		full_path = os.path.join(project_dir, name)
		if os.path.isdir(full_path):
			shutil.rmtree(full_path)

	for entry in pathlib.Path(project_dir).iterdir():
		if entry.name.endswith(".egg-info"):
			if entry.is_dir():
				shutil.rmtree(entry)
			elif entry.is_file():
				entry.unlink()

#============================================

def parse_pip_versions_output(output: str) -> tuple[list[str], str | None]:
	"""Parse pip index versions output.

	Args:
		output: Combined stdout and stderr from pip.

	Returns:
		Tuple of (available_versions, latest_version).
	"""
	available_versions: list[str] = []
	latest_version: str | None = None

	for line in output.splitlines():
		if "LATEST:" in line:
			match = re.search(r"LATEST:\s*([^\s]+)", line)
			if match:
				latest_version = match.group(1).strip()

	for line in output.splitlines():
		if "Available versions:" in line:
			match = re.search(r"Available versions:\s*(.+)", line)
			if match:
				version_text = match.group(1)
				version_list = [item.strip() for item in version_text.split(",") if item.strip()]
				available_versions = version_list

	if not available_versions and latest_version:
		available_versions = [latest_version]

	result = (available_versions, latest_version)
	return result

#============================================

def check_version_exists(
	python_exe: str,
	project_dir: str,
	package_name: str,
	version: str,
	index_url: str,
) -> None:
	"""Check if a version already exists on the repository.

	Args:
		python_exe: Python executable.
		project_dir: Project directory.
		package_name: Package name.
		version: Version string.
		index_url: Index URL to query.
	"""
	pypi_support.print_step("Checking for existing versions...")
	cmd = [
		python_exe,
		"-m",
		"pip",
		"index",
		"versions",
		package_name,
		"--index-url",
		index_url,
	]
	if Version(version).is_prerelease:
		cmd.append("--pre")
	result = pypi_support.run_command_allow_fail(cmd, project_dir, True)
	output = "\n".join([result.stdout, result.stderr])
	if result.returncode != 0:
		pypi_support.print_warning("Unable to check versions with pip index. Skipping version check.")
		return

	available_versions, latest_version = parse_pip_versions_output(output)
	if latest_version:
		pypi_support.print_info(f"Latest version on index: {latest_version}")
	normalized_version = normalize_version_string(version)
	if available_versions:
		normalized_versions: set[str] = set()
		for item in available_versions:
			try:
				normalized_versions.add(normalize_version_string(item))
			except InvalidVersion:
				normalized_versions.add(item)
		if normalized_version in normalized_versions:
			pypi_support.fail(f"Version {version} already exists on the index.")
	if not available_versions:
		pypi_support.print_warning("No versions reported by pip index.")

#============================================

def verify_dist_contents(dist_dir: str) -> None:
	"""Verify dist/ contains both wheel and sdist.

	Args:
		dist_dir: Dist directory.
	"""
	files = list_dist_files(dist_dir)
	wheel_ok = any(path.name.endswith(".whl") for path in files)
	sdist_ok = any(path.name.endswith(".tar.gz") for path in files)
	if not wheel_ok or not sdist_ok:
		pypi_support.fail("dist/ is missing a .whl or .tar.gz file.")

#============================================

def get_dist_args(dist_dir: str) -> list[str]:
	"""Return dist files as arguments for twine.

	Args:
		dist_dir: Dist directory.

	Returns:
		List of dist file paths.
	"""
	files = list_dist_files(dist_dir)
	if not files:
		pypi_support.fail("No distribution files found in dist/.")
	args = [str(path) for path in files]
	return args

#============================================

def build_package(python_exe: str, project_dir: str) -> None:
	"""Build the package.

	Args:
		python_exe: Python executable.
		project_dir: Project directory.
	"""
	pypi_support.print_step("Building the package...")
	log_path = os.path.join(project_dir, BUILD_LOG_NAME)
	with open(log_path, "w") as handle:
		handle.write(
			f"Build log ({datetime.datetime.now().isoformat()})\n"
		)
	pypi_support.print_info(f"Build output: {log_path}")
	pypi_support.run_command_to_log([python_exe, "-m", "build"], project_dir, log_path)

#============================================

def check_metadata(python_exe: str, project_dir: str) -> None:
	"""Run twine check on dist artifacts.

	Args:
		python_exe: Python executable.
		project_dir: Project directory.
	"""
	pypi_support.print_step("Checking package metadata...")
	dist_dir = os.path.join(project_dir, "dist")
	dist_args = get_dist_args(dist_dir)
	command = [python_exe, "-m", "twine", "check"]
	command.extend(dist_args)
	pypi_support.run_command(command, project_dir, False)

#============================================


def upload_package(
	python_exe: str,
	project_dir: str,
	upload_url: str,
	username: str,
	password: str,
	verbose: bool,
) -> None:
	"""Upload the package with twine, injecting credentials via environment.

	Args:
		python_exe: Python executable.
		project_dir: Project directory.
		upload_url: The upload endpoint URL.
		username: PyPI username (usually '__token__').
		password: PyPI API token.
		verbose: True to pass verbose output through from Twine.
	"""
	pypi_support.print_step("Uploading the package...")
	dist_dir = os.path.join(project_dir, "dist")
	dist_args = get_dist_args(dist_dir)
	cmd = [python_exe, "-m", "twine", "upload"]
	if verbose:
		cmd.append("--verbose")
	cmd.extend(["--repository-url", upload_url])
	cmd.extend(dist_args)
	# Inject credentials via environment so twine does not need [distutils]
	env = os.environ.copy()
	env["TWINE_USERNAME"] = username
	env["TWINE_PASSWORD"] = password
	result = subprocess.run(cmd, cwd=project_dir, text=True, env=env)
	if result.returncode != 0:
		command_text = " ".join(cmd)
		if verbose:
			pypi_support.fail(f"Command failed: {command_text}")
		pypi_support.fail(f"Command failed: {command_text}\nRerun this script with --verbose for Twine diagnostics.")

#============================================

def get_venv_python(venv_dir: str) -> str:
	"""Get the python executable in a venv.

	Args:
		venv_dir: Path to the venv directory.

	Returns:
		The python executable path.
	"""
	if os.name == "nt":
		python_path = os.path.join(venv_dir, "Scripts", "python.exe")
		return python_path
	python_path = os.path.join(venv_dir, "bin", "python")
	return python_path

#============================================

def test_install(
	python_exe: str,
	project_dir: str,
	package_name: str,
	import_name: str,
	index_url: str,
	version: str,
) -> None:
	"""Test install the package in a temporary venv.

	Args:
		python_exe: Python executable.
		project_dir: Project directory.
		package_name: Package name.
		import_name: Import name.
		index_url: Index URL.
	"""
	pypi_support.print_step("Testing install in a temporary venv...")
	with tempfile.TemporaryDirectory(prefix="pypi_upload_") as temp_dir:
		venv_dir = os.path.join(temp_dir, "venv")
		pypi_support.run_command([python_exe, "-m", "venv", venv_dir], project_dir, False)

		venv_python = get_venv_python(venv_dir)
		pypi_support.run_command([venv_python, "-m", "pip", "install", "--upgrade", "pip"], project_dir, False)
		normalized_version = normalize_version_string(version)
		install_command = [
			venv_python,
			"-m",
			"pip",
			"install",
			"--no-deps",
			"--no-cache-dir",
			"--force-reinstall",
			"--index-url",
			index_url,
			f"{package_name}=={normalized_version}",
		]
		if Version(version).is_prerelease:
			install_command.insert(4, "--pre")
		time.sleep(2)
		for attempt in range(1, TEST_INSTALL_RETRIES + 1):
			result = pypi_support.run_command_allow_fail(install_command, project_dir, True)
			if result.returncode == 0:
				break
			output = "\n".join([result.stdout, result.stderr])
			if "No matching distribution found" not in output:
				pypi_support.fail(f"Test install failed. Output:\n{output}")
			if attempt >= TEST_INSTALL_RETRIES:
				pypi_support.fail("Test install failed after retries. Package may not be indexed yet.")
			pypi_support.print_warning(
				"Test install did not find the new version yet. "
				f"Retrying in {TEST_INSTALL_RETRY_DELAY}s..."
			)
			time.sleep(TEST_INSTALL_RETRY_DELAY)

		import_command = f"import {import_name}; print('{import_name} successfully installed')"
		pypi_support.run_command([venv_python, "-c", import_command], project_dir, False)

#============================================

def resolve_project_url(repo: str, package_name: str, version: str) -> str:
	"""Resolve the project page URL."""
	normalized_version = normalize_version_string(version)
	if pypi_auth.is_pypi_repo(repo):
		return f"{PYPI_PROJECT_BASE}{canonicalize_name(package_name)}/{normalized_version}/"
	return f"{TESTPYPI_PROJECT_BASE}{canonicalize_name(package_name)}/{normalized_version}/"

#============================================

def open_project_url(url: str) -> None:
	"""Open the project URL in a browser when possible.

	Args:
		url: The URL to open.
	"""
	if not url:
		pypi_support.print_warning("No project URL to open.")
		return

	cmd: list[str] | None = None
	if sys.platform.startswith("darwin"):
		if shutil.which("open"):
			cmd = ["open", url]
	elif sys.platform.startswith("linux"):
		if shutil.which("xdg-open"):
			cmd = ["xdg-open", url]
	elif os.name == "nt":
		cmd = ["cmd", "/c", "start", "", url]

	if not cmd:
		pypi_support.print_warning("No browser opener found. Skipping.")
		return

	result = pypi_support.run_command_allow_fail(cmd, os.getcwd(), False)
	if result.returncode != 0:
		pypi_support.print_warning("Browser open command failed.")

#============================================

def main() -> None:
	args = parse_args()
	# Resolve repo: --repo overrides, otherwise derive from --main/--test
	if args.repo_override:
		args.repo = args.repo_override
	elif args.use_main:
		args.repo = "pypi"
	else:
		args.repo = "testpypi"

	project_dir = resolve_repo_root()
	pyproject_path = resolve_pyproject_path(project_dir)

	pyproject_data = read_pyproject(pyproject_path)
	metadata_name, metadata_version = extract_project_metadata(pyproject_data)

	package_name = resolve_package_name(metadata_name)
	version = resolve_version(metadata_version)
	import_name = resolve_import_name("", package_name)
	index_url = pypi_auth.resolve_index_url(args.repo)
	version_file = version_lib.read_version_file(project_dir)
	version_lib.verify_version_sync(version, version_file)
	validate_version_string(version)
	requires_python = read_requires_python(pyproject_data)

	pypi_support.print_step("Project info")
	pypi_support.print_info(f"Project dir: {project_dir}")
	pypi_support.print_info(f"pyproject: {pyproject_path}")
	pypi_support.print_info(f"Package name: {package_name}")
	pypi_support.print_info(f"Version: {version}")
	pypi_support.print_info(f"Normalized version: {normalize_version_string(version)}")
	pypi_support.print_info(f"VERSION file: {version_file}")
	pypi_support.print_info(f"Import name: {import_name}")
	pypi_support.print_info(f"Repository: {args.repo}")
	pypi_support.print_info(f"Index URL: {index_url}")

	if args.set_version:
		new_version = args.set_version.strip()
		if not new_version:
			pypi_support.fail("Set-version value cannot be empty.")
		validate_version_string(new_version)
		pypi_support.print_step("Setting version")
		require_git_clean(project_dir)
		require_main_branch(project_dir)
		require_up_to_date_with_origin_main(project_dir)
		update_version_files(project_dir, new_version)
		did_commit = commit_version_bump(project_dir, new_version)
		tag_and_push_version(project_dir, new_version, did_commit)
		pypi_support.print_info(f"Version updated and pushed: {new_version}")
		return

	pypi_support.print_step("Pre-checks")
	require_python_version(requires_python)
	require_git_clean(project_dir)
	require_main_branch(project_dir)
	require_up_to_date_with_origin_main(project_dir)
	require_version_tag(project_dir, version)
	require_twine_available(sys.executable, project_dir)
	# Validate token and possibly prompt user to select a different section
	args.repo, twine_username, twine_password, pypirc_url = pypi_auth.require_pypirc_token(
		args.repo, package_name
	)
	index_url = pypi_auth.resolve_index_url(args.repo)
	pypi_auth.require_index_reachable(index_url)
	require_editable_install_in_sync(sys.executable, project_dir, package_name, version)
	require_pytest_passes_if_available(sys.executable, project_dir)

	check_version_exists(sys.executable, project_dir, package_name, version, index_url)
	if args.check_only:
		pypi_support.print_step("Check-only mode: exiting after version check.")
		return

	pypi_support.print_step("Upgrading build tools (excluding pip)...")
	log_path = os.path.join(project_dir, BUILD_LOG_NAME)
	with open(log_path, "a") as handle:
		handle.write("\nUpgrade tools output\n")
	pypi_support.print_info(f"Build output: {log_path}")
	build_tools = ["setuptools", "wheel", "build", "twine"]
	pypi_support.run_command_to_log(
		[sys.executable, "-m", "pip", "install", "--upgrade"] + build_tools,
		project_dir,
		log_path,
	)

	pypi_support.print_step("Cleaning build artifacts...")
	clean_build_artifacts(project_dir)
	require_dist_empty(project_dir)

	build_package(sys.executable, project_dir)

	pypi_support.print_step("Verifying dist/ contents...")
	verify_dist_contents(os.path.join(project_dir, "dist"))
	show_dist_files(os.path.join(project_dir, "dist"))

	check_metadata(sys.executable, project_dir)
	if args.build_only:
		pypi_support.print_step("Build-only mode: skipping upload and test install.")
		return

	# Show resolved upload target
	upload_url = pypi_auth.resolve_upload_url(args.repo, pypirc_url)
	pypi_support.print_step("Upload target")
	pypi_support.print_info(f"Repository: {args.repo}")
	pypi_support.print_info(f"Upload URL: {upload_url}")
	pypi_support.print_info(f"Package: {package_name}")
	pypi_support.print_info(f"Version: {normalize_version_string(version)}")

	# Require confirmation for production PyPI uploads
	if pypi_auth.is_pypi_repo(args.repo):
		answer = input("Upload to production PyPI? Type 'yes' to confirm: ").strip()
		if answer.lower() != "yes":
			pypi_support.fail("Aborted. Did not confirm production upload.")

	upload_package(
		sys.executable,
		project_dir,
		upload_url,
		twine_username,
		twine_password,
		args.verbose_upload,
	)

	test_install(sys.executable, project_dir, package_name, import_name, index_url, version)

	project_url = resolve_project_url(args.repo, package_name, version)
	if project_url:
		pypi_support.print_info(f"Project URL: {project_url}")
	open_project_url(project_url)

	if not pypi_auth.is_pypi_repo(args.repo):
		pypi_support.print_step("Next step")
		pypi_support.print_info("If everything looks good, upload to PyPI with:")
		pypi_support.print_info("python3 devel/submit_to_pypi.py --repo pypi")

#============================================

if __name__ == "__main__":
	main()
