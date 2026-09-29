# This file is vendored. Local changes can and will be overwritten by propagation.

"""Build, inspect, upload, and installation-test PyPI distributions."""

# Standard Library
import os
import re
import time
import shutil
import pathlib
import datetime
import tempfile
import subprocess

# PIP3 modules
from packaging.version import InvalidVersion, Version

# local repo modules
import pypi_project
import pypi_support


BUILD_LOG_NAME = "build_output.log"
TEST_INSTALL_RETRIES = 6
TEST_INSTALL_RETRY_DELAY = 10


#============================================
def format_bytes(size_bytes: int) -> str:
	"""Format byte counts for human-readable output."""
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
	"""Return the sorted regular files in dist/."""
	dist_path = pathlib.Path(dist_dir)
	if not dist_path.exists():
		return []
	files = sorted([path for path in dist_path.iterdir() if path.is_file()])
	return files


#============================================
def show_dist_files(dist_dir: str) -> None:
	"""Print distribution filenames and sizes."""
	files = list_dist_files(dist_dir)
	if not files:
		pypi_support.print_warning("No distribution files found in dist/.")
		return
	for path in files:
		size_text = format_bytes(path.stat().st_size)
		pypi_support.print_info(f"dist/{path.name} ({size_text})")


#============================================
def clean_build_artifacts(project_dir: str) -> None:
	"""Remove build, dist, and root egg-info artifacts."""
	for name in ["build", "dist"]:
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
def require_dist_empty(project_dir: str) -> None:
	"""Ensure dist/ is empty after cleaning."""
	dist_dir = os.path.join(project_dir, "dist")
	if not os.path.isdir(dist_dir):
		return
	entries = [name for name in os.listdir(dist_dir) if not name.startswith(".")]
	if entries:
		joined = ", ".join(sorted(entries))
		pypi_support.fail(f"dist/ is not empty after cleaning: {joined}")


#============================================
def parse_pip_versions_output(output: str) -> tuple[list[str], str | None]:
	"""Parse available and latest versions from pip index output."""
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
				available_versions = [
					item.strip() for item in version_text.split(",") if item.strip()
				]
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
	"""Fail when the requested version already exists on the package index."""
	pypi_support.print_step("Checking for existing versions...")
	command = [
		python_exe, "-m", "pip", "index", "versions", package_name,
		"--index-url", index_url,
	]
	if Version(version).is_prerelease:
		command.append("--pre")
	result = pypi_support.run_command_allow_fail(command, project_dir, True)
	output = "\n".join([result.stdout, result.stderr])
	if result.returncode != 0:
		pypi_support.print_warning("Unable to check versions with pip index. Skipping version check.")
		return

	available_versions, latest_version = parse_pip_versions_output(output)
	normalized_version = pypi_project.normalize_version_string(version)
	if latest_version:
		pypi_support.print_info(f"Latest version on index: {latest_version}")
	if available_versions:
		normalized_versions: set[str] = set()
		for item in available_versions:
			try:
				normalized_versions.add(pypi_project.normalize_version_string(item))
			except InvalidVersion:
				normalized_versions.add(item)
		if normalized_version in normalized_versions:
			pypi_support.fail(f"Version {version} already exists on the index.")
	if not available_versions:
		pypi_support.print_warning("No versions reported by pip index.")


#============================================
def verify_dist_contents(dist_dir: str) -> None:
	"""Ensure dist/ contains both a wheel and source distribution."""
	files = list_dist_files(dist_dir)
	wheel_ok = any(path.name.endswith(".whl") for path in files)
	sdist_ok = any(path.name.endswith(".tar.gz") for path in files)
	if not wheel_ok or not sdist_ok:
		pypi_support.fail("dist/ is missing a .whl or .tar.gz file.")


#============================================
def get_dist_args(dist_dir: str) -> list[str]:
	"""Return distribution files as Twine command arguments."""
	files = list_dist_files(dist_dir)
	if not files:
		pypi_support.fail("No distribution files found in dist/.")
	args = [str(path) for path in files]
	return args


#============================================
def upgrade_build_tools(python_exe: str, project_dir: str) -> None:
	"""Upgrade package-building tools and append output to the build log."""
	pypi_support.print_step("Upgrading build tools (excluding pip)...")
	log_path = os.path.join(project_dir, BUILD_LOG_NAME)
	with open(log_path, "a") as handle:
		handle.write("\nUpgrade tools output\n")
	pypi_support.print_info(f"Build output: {log_path}")
	build_tools = ["setuptools", "wheel", "build", "twine"]
	command = [python_exe, "-m", "pip", "install", "--upgrade"] + build_tools
	pypi_support.run_command_to_log(command, project_dir, log_path)


#============================================
def build_package(python_exe: str, project_dir: str) -> None:
	"""Build the package and replace the build log."""
	pypi_support.print_step("Building the package...")
	log_path = os.path.join(project_dir, BUILD_LOG_NAME)
	with open(log_path, "w") as handle:
		handle.write(f"Build log ({datetime.datetime.now().isoformat()})\n")
	pypi_support.print_info(f"Build output: {log_path}")
	pypi_support.run_command_to_log([python_exe, "-m", "build"], project_dir, log_path)


#============================================
def check_metadata(python_exe: str, project_dir: str) -> None:
	"""Run Twine's metadata check on every distribution artifact."""
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
	"""Upload distribution artifacts with credentials isolated in the environment.

	Args:
		python_exe: Python executable used to run Twine.
		project_dir: Repository root containing the dist directory.
		upload_url: Package-index upload endpoint.
		username: Twine repository username.
		password: Twine token supplied only through the subprocess environment.
		verbose: Whether Twine should emit verbose diagnostics.

	Raises:
		RuntimeError: When Twine returns a nonzero status.
	"""
	pypi_support.print_step("Uploading the package...")
	dist_args = get_dist_args(os.path.join(project_dir, "dist"))
	command = [python_exe, "-m", "twine", "upload"]
	if verbose:
		command.append("--verbose")
	command.extend(["--repository-url", upload_url])
	command.extend(dist_args)
	# ASVS 13.3.1 and 14.2.4: keep the token out of source, argv, and logs.
	environment = os.environ.copy()
	environment["TWINE_USERNAME"] = username
	environment["TWINE_PASSWORD"] = password
	result = subprocess.run(command, cwd=project_dir, text=True, env=environment)
	if result.returncode != 0:
		command_text = " ".join(command)
		if verbose:
			pypi_support.fail(f"Command failed: {command_text}")
		pypi_support.fail(
			f"Command failed: {command_text}\n"
			"Rerun this script with --verbose for Twine diagnostics."
		)


#============================================
def get_venv_python(venv_dir: str) -> str:
	"""Return the platform-specific Python executable in a virtual environment."""
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
	"""Install the uploaded version in a temporary environment and import it.

	Creates an isolated virtual environment, retries while the index publishes
	the new artifact, and removes the environment on completion.

	Args:
		python_exe: Python executable used to create the temporary environment.
		project_dir: Repository root used as the subprocess working directory.
		package_name: Distribution name and version specifier base.
		import_name: Dotted Python name imported after installation.
		index_url: Package-index URL used by pip.
		version: Exact uploaded version to install.

	Raises:
		RuntimeError: When installation retries expire or the installed import fails.
	"""
	pypi_support.print_step("Testing install in a temporary venv...")
	with tempfile.TemporaryDirectory(prefix="pypi_upload_") as temp_dir:
		venv_dir = os.path.join(temp_dir, "venv")
		pypi_support.run_command([python_exe, "-m", "venv", venv_dir], project_dir, False)
		venv_python = get_venv_python(venv_dir)
		upgrade_pip = [venv_python, "-m", "pip", "install", "--upgrade", "pip"]
		pypi_support.run_command(upgrade_pip, project_dir, False)
		normalized_version = pypi_project.normalize_version_string(version)
		install_command = [
			venv_python, "-m", "pip", "install", "--no-deps", "--no-cache-dir",
			"--force-reinstall", "--index-url", index_url,
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
				pypi_support.fail(
					"Test install failed after retries. Package may not be indexed yet."
				)
			pypi_support.print_warning(
				"Test install did not find the new version yet. "
				f"Retrying in {TEST_INSTALL_RETRY_DELAY}s..."
			)
			time.sleep(TEST_INSTALL_RETRY_DELAY)

		# Pass the validated import name as data, not executable Python source.
		import_script = (
			"import importlib, sys; importlib.import_module(sys.argv[1]); "
			"print(f'{sys.argv[1]} successfully installed')"
		)
		import_command = [venv_python, "-c", import_script, import_name]
		pypi_support.run_command(import_command, project_dir, False)
