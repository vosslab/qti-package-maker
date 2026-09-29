# This file is vendored. Local changes can and will be overwritten by propagation.

"""Load and update the local project metadata used by PyPI publishing."""

# Standard Library
import os
import re
import sys
import pathlib
import tomllib
import dataclasses

# PIP3 modules
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

# local repo modules
import pypi_support
import version_lib


IMPORT_NAME_PATTERN = re.compile(
	r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)


@dataclasses.dataclass(frozen=True)
class ProjectInfo:
	"""Validated local project metadata required by the publishing workflow."""

	project_dir: str
	pyproject_path: str
	package_name: str
	version: str
	import_name: str
	requires_python: str
	version_file: str


#============================================
def resolve_repo_root() -> str:
	"""Resolve the repository root through Git."""
	result = pypi_support.run_command_allow_fail(
		["git", "rev-parse", "--show-toplevel"], os.getcwd(), True,
	)
	if result.returncode != 0 or not result.stdout.strip():
		pypi_support.fail("Unable to resolve the Git repository root.")
	# ASVS 5.3.2: derive project file paths from the trusted Git root.
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
	"""Load pyproject.toml into a dict."""
	with open(pyproject_path, "rb") as handle:
		data = tomllib.load(handle)
	return data


#============================================
def extract_project_metadata(pyproject_data: dict) -> tuple[str | None, str | None]:
	"""Extract package name and version from project or Poetry metadata."""
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
	"""Require and return the package name from project metadata."""
	name = metadata_name or ""
	if not name:
		pypi_support.fail("Package name not found in pyproject.toml.")
	return name


#============================================
def resolve_version(metadata_version: str | None) -> str:
	"""Require and return the version from project metadata."""
	version = metadata_version or ""
	if not version:
		pypi_support.fail("Package version not found in pyproject.toml.")
	return version


#============================================
def resolve_import_name(arg_value: str, package_name: str) -> str:
	"""Resolve and validate the dotted Python name used by import checks."""
	import_name = arg_value.strip() if arg_value else ""
	if not import_name:
		import_name = re.sub(r"[-.]", "_", package_name)
	# ASVS 2.2.1: accept only dotted Python identifiers at the command boundary.
	if not IMPORT_NAME_PATTERN.fullmatch(import_name):
		pypi_support.fail(f"Invalid Python import name: {import_name}")
	return import_name


#============================================
def validate_version_string(version: str) -> None:
	"""Validate that the version string parses as PEP 440."""
	try:
		Version(version)
	except InvalidVersion as exc:
		pypi_support.fail(f"Invalid version string: {version} ({exc})")


#============================================
def normalize_version_string(version: str) -> str:
	"""Return the normalized PEP 440 version string."""
	return str(Version(version))


#============================================
def read_requires_python(pyproject_data: dict) -> str:
	"""Read the requires-python field from pyproject data."""
	project_data = pyproject_data.get("project", {})
	requires_python = project_data.get("requires-python", "")
	return str(requires_python).strip()


#============================================
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


#============================================
def load_project(project_dir: str) -> ProjectInfo:
	"""Load and validate all local project metadata needed by publishing.

	Args:
		project_dir: Repository root containing pyproject.toml and VERSION.

	Returns:
		ProjectInfo: Validated metadata and paths for the publishing workflow.

	Raises:
		RuntimeError: When required metadata is missing, invalid, or inconsistent.
	"""
	pyproject_path = resolve_pyproject_path(project_dir)
	pyproject_data = read_pyproject(pyproject_path)
	metadata_name, metadata_version = extract_project_metadata(pyproject_data)
	package_name = resolve_package_name(metadata_name)
	version = resolve_version(metadata_version)
	import_name = resolve_import_name("", package_name)
	validate_version_string(version)
	version_file = version_lib.read_version_file(project_dir)
	version_lib.verify_version_sync(version, version_file)
	project = ProjectInfo(
		project_dir=project_dir,
		pyproject_path=pyproject_path,
		package_name=package_name,
		version=version,
		import_name=import_name,
		requires_python=read_requires_python(pyproject_data),
		version_file=version_file,
	)
	return project


#============================================
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
		contents, ["project", "tool.poetry"], version,
	)
	if not changed:
		pypi_support.fail("Unable to update version in pyproject.toml.")
	if updated != contents:
		with open(pyproject_path, "w") as handle:
			handle.write(updated)
