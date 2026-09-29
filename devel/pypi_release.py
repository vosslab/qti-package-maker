# This file is vendored. Local changes can and will be overwritten by propagation.

"""Enforce Git and local-environment preconditions for PyPI releases."""

# PIP3 modules
from packaging.version import Version

# local repo modules
import pypi_project
import pypi_support


# ASVS 1.2.5: every OS command in this module uses an argument list without a shell.


#============================================
def require_git_clean(project_dir: str) -> None:
	"""Ensure the Git working tree has no staged or unstaged tracked changes."""
	result = pypi_support.run_command_allow_fail(
		["git", "status", "--porcelain", "--untracked-files=no"], project_dir, True,
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


#============================================
def require_main_branch(project_dir: str) -> None:
	"""Ensure the release is on the main branch."""
	result = pypi_support.run_command_allow_fail(
		["git", "rev-parse", "--abbrev-ref", "HEAD"], project_dir, True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to determine current git branch.")
	branch = result.stdout.strip()
	if branch != "main":
		pypi_support.fail(f"Release must be cut from main. Current branch: {branch}")


#============================================
def require_version_tag(project_dir: str, version: str) -> None:
	"""Ensure the Git tag for the version exists."""
	tag_name = f"v{version}"
	result = pypi_support.run_command_allow_fail(
		["git", "tag", "--list", tag_name], project_dir, True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to check git tags.")
	if not result.stdout.strip():
		pypi_support.fail(
			"Missing version tag. Create it with:\n"
			f"git tag -a {tag_name} -m \"Release {tag_name}\"\n"
			f"git push origin {tag_name}"
		)


#============================================
def require_twine_available(python_exe: str, project_dir: str) -> None:
	"""Ensure Twine is installed and runnable."""
	command = [python_exe, "-m", "twine", "--version"]
	result = pypi_support.run_command_allow_fail(command, project_dir, True)
	if result.returncode != 0:
		pypi_support.fail("twine is not available. Install it with: python -m pip install twine")


#============================================
def require_editable_install_in_sync(
	python_exe: str,
	project_dir: str,
	package_name: str,
	version: str,
) -> None:
	"""Ensure an installed editable package matches the repository version.

	The check is skipped when the package is not installed in the active Python
	environment. A present package must report the repository version.

	Args:
		python_exe: Python executable used to inspect installed packages.
		project_dir: Repository root used as the subprocess working directory.
		package_name: Distribution name recorded in project metadata.
		version: Expected repository version.

	Raises:
		RuntimeError: When an installed package reports a different version.
	"""
	import_name = pypi_project.resolve_import_name("", package_name)
	find_import = (
		"import importlib.util, sys; "
		"sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)"
	)
	check_command = [python_exe, "-c", find_import, import_name]
	result = pypi_support.run_command_allow_fail(check_command, project_dir, True)
	if result.returncode != 0:
		return

	read_version = (
		"import importlib.metadata, sys; "
		"print(importlib.metadata.version(sys.argv[1]))"
	)
	version_command = [python_exe, "-c", read_version, package_name]
	result = pypi_support.run_command_allow_fail(version_command, project_dir, True)
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
	"""Run pytest when it is installed."""
	check_command = [python_exe, "-c", "import pytest"]
	result = pypi_support.run_command_allow_fail(check_command, project_dir, False)
	if result.returncode != 0:
		pypi_support.print_warning("pytest not installed; skipping tests.")
		return
	pypi_support.print_step("Running pytest...")
	pypi_support.run_command([python_exe, "-m", "pytest", "-q"], project_dir, False)


#============================================
def require_up_to_date_with_origin_main(project_dir: str) -> None:
	"""Ensure local main is synchronized with origin/main."""
	fetch_result = pypi_support.run_command_allow_fail(
		["git", "fetch", "origin", "main"], project_dir, True,
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
			"Local main has commits not pushed to origin/main. Run: git push origin main"
		)
	if behind > 0 and ahead == 0:
		pypi_support.fail(
			"Local main is behind origin/main. Run: git pull --ff-only origin main"
		)
	pypi_support.fail(
		"Local main has diverged from origin/main. Run: git pull --rebase origin main"
	)


#============================================
def has_tracked_changes(project_dir: str) -> bool:
	"""Return whether Git reports staged or unstaged tracked changes."""
	result = pypi_support.run_command_allow_fail(
		["git", "status", "--porcelain", "--untracked-files=no"], project_dir, True,
	)
	if result.returncode != 0:
		pypi_support.fail("Unable to check git status.")
	return bool(result.stdout.strip())


#============================================
def commit_version_bump(project_dir: str, version: str) -> bool:
	"""Commit the version bump when version files changed."""
	pypi_support.run_command(["git", "add", "VERSION", "pyproject.toml"], project_dir, False)
	if not has_tracked_changes(project_dir):
		pypi_support.print_warning("Version files already match; skipping commit.")
		return False
	pypi_support.run_command(
		["git", "commit", "-m", f"Bump version to {version}"], project_dir, False,
	)
	return True


#============================================
def tag_and_push_version(project_dir: str, version: str, push_main: bool) -> None:
	"""Create the version tag when needed, then push the commit and tag."""
	tag_name = f"v{version}"
	tag_result = pypi_support.run_command_allow_fail(
		["git", "tag", "--list", tag_name], project_dir, True,
	)
	if tag_result.returncode != 0:
		pypi_support.fail("Unable to check git tags.")
	if not tag_result.stdout.strip():
		pypi_support.run_command(
			["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
			project_dir,
			False,
		)
	if push_main:
		pypi_support.run_command(["git", "push", "origin", "main"], project_dir, False)
	pypi_support.run_command(["git", "push", "origin", tag_name], project_dir, False)


#============================================
def set_and_publish_version(project_dir: str, version: str) -> None:
	"""Validate, write, commit, tag, and push a requested version."""
	pypi_project.validate_version_string(version)
	require_git_clean(project_dir)
	require_main_branch(project_dir)
	require_up_to_date_with_origin_main(project_dir)
	pypi_project.update_version_files(project_dir, version)
	did_commit = commit_version_bump(project_dir, version)
	tag_and_push_version(project_dir, version, did_commit)
