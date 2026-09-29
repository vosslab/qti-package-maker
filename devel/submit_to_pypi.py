#!/usr/bin/env python3
# This file is vendored. Local changes can and will be overwritten by propagation.

"""Coordinate validated project, release, and distribution steps for PyPI."""

# Standard Library
import os
import sys
import shutil
import argparse

# PIP3 modules
from packaging.utils import canonicalize_name

# local repo modules
import pypi_auth
import pypi_project
import pypi_release
import pypi_support
import pypi_distribution


TESTPYPI_PROJECT_BASE = "https://test.pypi.org/project/"
PYPI_PROJECT_BASE = "https://pypi.org/project/"


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse the repository and release-mode arguments."""
	parser = argparse.ArgumentParser(
		description="Build and upload a Python package to PyPI or TestPyPI.",
	)
	repo_group = parser.add_argument_group("repository")
	mode_group = repo_group.add_mutually_exclusive_group()
	mode_group.add_argument(
		"-t", "--test", dest="use_main", action="store_false",
		help="Upload to TestPyPI (default).",
	)
	mode_group.add_argument(
		"-m", "--main", dest="use_main", action="store_true",
		help="Upload to production PyPI.",
	)
	repo_group.add_argument(
		"-r", "--repo", dest="repo_override", default="",
		help="Override: use a specific ~/.pypirc section name.",
	)
	parser.set_defaults(use_main=False)
	behavior_group = parser.add_argument_group("behavior")
	behavior_group.add_argument(
		"--version-check", dest="check_only",
		help="Check if the version exists on the index and exit.", action="store_true",
	)
	behavior_group.add_argument(
		"--build-only", dest="build_only",
		help="Run all build steps but skip upload and test install.", action="store_true",
	)
	behavior_group.add_argument(
		"--verbose", dest="verbose_upload",
		help="Show verbose Twine output during upload.", action="store_true",
	)
	behavior_group.add_argument(
		"--set-version", dest="set_version",
		help="Update VERSION and pyproject.toml, then tag and push.", default="",
	)
	args = parser.parse_args()
	return args


#============================================
def resolve_repository(args: argparse.Namespace) -> str:
	"""Resolve the requested .pypirc repository section."""
	if args.repo_override:
		return args.repo_override
	if args.use_main:
		return "pypi"
	return "testpypi"


#============================================
def print_project_info(project: pypi_project.ProjectInfo, repo: str, index_url: str) -> None:
	"""Display the validated project and selected repository."""
	pypi_support.print_step("Project info")
	pypi_support.print_info(f"Project dir: {project.project_dir}")
	pypi_support.print_info(f"pyproject: {project.pyproject_path}")
	pypi_support.print_info(f"Package name: {project.package_name}")
	pypi_support.print_info(f"Version: {project.version}")
	normalized_version = pypi_project.normalize_version_string(project.version)
	pypi_support.print_info(f"Normalized version: {normalized_version}")
	pypi_support.print_info(f"VERSION file: {project.version_file}")
	pypi_support.print_info(f"Import name: {project.import_name}")
	pypi_support.print_info(f"Repository: {repo}")
	pypi_support.print_info(f"Index URL: {index_url}")


#============================================
def resolve_project_url(repo: str, package_name: str, version: str) -> str:
	"""Resolve the canonical package-version page URL."""
	normalized_version = pypi_project.normalize_version_string(version)
	canonical_name = canonicalize_name(package_name)
	if pypi_auth.is_pypi_repo(repo):
		return f"{PYPI_PROJECT_BASE}{canonical_name}/{normalized_version}/"
	return f"{TESTPYPI_PROJECT_BASE}{canonical_name}/{normalized_version}/"


#============================================
def open_project_url(url: str) -> None:
	"""Open the known PyPI project URL in a browser when possible."""
	command: list[str] | None = None
	if sys.platform.startswith("darwin") and shutil.which("open"):
		command = ["open", url]
	elif sys.platform.startswith("linux") and shutil.which("xdg-open"):
		command = ["xdg-open", url]
	elif os.name == "nt":
		command = ["cmd", "/c", "start", "", url]
	if not command:
		pypi_support.print_warning("No browser opener found. Skipping.")
		return
	result = pypi_support.run_command_allow_fail(command, os.getcwd(), False)
	if result.returncode != 0:
		pypi_support.print_warning("Browser open command failed.")


#============================================
def run_version_update(project: pypi_project.ProjectInfo, requested_version: str) -> None:
	"""Run the explicit version-update workflow and report completion."""
	new_version = requested_version.strip()
	if not new_version:
		pypi_support.fail("Set-version value cannot be empty.")
	pypi_support.print_step("Setting version")
	pypi_release.set_and_publish_version(project.project_dir, new_version)
	pypi_support.print_info(f"Version updated and pushed: {new_version}")


#============================================
def run_prechecks(
	project: pypi_project.ProjectInfo,
	repo: str,
) -> tuple[str, str, str, str, str]:
	"""Run release gates in order and return validated repository credentials.

	Args:
		project: Validated local project metadata and paths.
		repo: Requested .pypirc repository section.

	Returns:
		tuple: Repository name, username, token, upload URL, and index URL.

	Raises:
		RuntimeError: When a release gate, credential check, or test fails.
	"""
	# ASVS 2.3.1: every state and test gate completes before build or upload.
	pypi_support.print_step("Pre-checks")
	pypi_project.require_python_version(project.requires_python)
	pypi_release.require_git_clean(project.project_dir)
	pypi_release.require_main_branch(project.project_dir)
	pypi_release.require_up_to_date_with_origin_main(project.project_dir)
	pypi_release.require_version_tag(project.project_dir, project.version)
	pypi_release.require_twine_available(sys.executable, project.project_dir)
	resolved_repo, username, password, pypirc_url = pypi_auth.require_pypirc_token(
		repo, project.package_name,
	)
	index_url = pypi_auth.resolve_index_url(resolved_repo)
	pypi_auth.require_index_reachable(index_url)
	pypi_release.require_editable_install_in_sync(
		sys.executable, project.project_dir, project.package_name, project.version,
	)
	pypi_release.require_pytest_passes_if_available(sys.executable, project.project_dir)
	result = (resolved_repo, username, password, pypirc_url, index_url)
	return result


#============================================
def build_distribution(project: pypi_project.ProjectInfo) -> None:
	"""Upgrade build tools, clean old outputs, build, and verify artifacts."""
	pypi_distribution.upgrade_build_tools(sys.executable, project.project_dir)
	pypi_support.print_step("Cleaning build artifacts...")
	pypi_distribution.clean_build_artifacts(project.project_dir)
	pypi_distribution.require_dist_empty(project.project_dir)
	pypi_distribution.build_package(sys.executable, project.project_dir)
	dist_dir = os.path.join(project.project_dir, "dist")
	pypi_support.print_step("Verifying dist/ contents...")
	pypi_distribution.verify_dist_contents(dist_dir)
	pypi_distribution.show_dist_files(dist_dir)
	pypi_distribution.check_metadata(sys.executable, project.project_dir)


#============================================
def confirm_production_upload(repo: str) -> None:
	"""Require exact human confirmation before a production PyPI upload."""
	if not pypi_auth.is_pypi_repo(repo):
		return
	answer = input("Upload to production PyPI? Type 'yes' to confirm: ").strip()
	if answer.lower() != "yes":
		pypi_support.fail("Aborted. Did not confirm production upload.")


#============================================
def main() -> None:
	"""Coordinate version, preflight, build, upload, and verification workflows."""
	args = parse_args()
	repo = resolve_repository(args)
	project_dir = pypi_project.resolve_repo_root()
	project = pypi_project.load_project(project_dir)
	index_url = pypi_auth.resolve_index_url(repo)
	print_project_info(project, repo, index_url)
	if args.set_version:
		run_version_update(project, args.set_version)
		return

	repo, username, password, pypirc_url, index_url = run_prechecks(project, repo)
	pypi_distribution.check_version_exists(
		sys.executable, project.project_dir, project.package_name,
		project.version, index_url,
	)
	if args.check_only:
		pypi_support.print_step("Check-only mode: exiting after version check.")
		return

	build_distribution(project)
	if args.build_only:
		pypi_support.print_step("Build-only mode: skipping upload and test install.")
		return

	upload_url = pypi_auth.resolve_upload_url(repo, pypirc_url)
	pypi_support.print_step("Upload target")
	pypi_support.print_info(f"Repository: {repo}")
	pypi_support.print_info(f"Upload URL: {upload_url}")
	pypi_support.print_info(f"Package: {project.package_name}")
	normalized_version = pypi_project.normalize_version_string(project.version)
	pypi_support.print_info(f"Version: {normalized_version}")
	confirm_production_upload(repo)
	pypi_distribution.upload_package(
		sys.executable, project.project_dir, upload_url,
		username, password, args.verbose_upload,
	)
	pypi_distribution.test_install(
		sys.executable, project.project_dir, project.package_name,
		project.import_name, index_url, project.version,
	)

	project_url = resolve_project_url(repo, project.package_name, project.version)
	pypi_support.print_info(f"Project URL: {project_url}")
	open_project_url(project_url)
	if not pypi_auth.is_pypi_repo(repo):
		pypi_support.print_step("Next step")
		pypi_support.print_info("If everything looks good, upload to PyPI with:")
		pypi_support.print_info("python3 devel/submit_to_pypi.py --repo pypi")


#============================================
if __name__ == "__main__":
	main()
