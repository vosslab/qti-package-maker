# Standard Library
import os
import sys
import pathlib
import zipfile
import subprocess

# Pip3 Library
import pytest


def assert_exists_and_nonempty(path: str) -> None:
	if not os.path.exists(path):
		raise FileNotFoundError(path)
	if os.path.getsize(path) <= 0:
		raise ValueError(f"Expected non-empty output file: {path}")


def assert_zip_has_manifest(zip_path: str) -> None:
	with zipfile.ZipFile(zip_path, "r") as zf:
		names = zf.namelist()
		if "imsmanifest.xml" not in names:
			raise ValueError(f"Missing imsmanifest.xml in {zip_path}")


@pytest.mark.smoke
def test_bbq_converter_all_types(tmp_path: pathlib.Path, sample_bbq_lines: list) -> None:
	tests_dir = os.path.abspath(os.path.dirname(__file__))
	repo_root = os.path.abspath(os.path.join(tests_dir, ".."))
	converter = os.path.join(repo_root, "tools", "bbq_converter.py")

	bbq_file = tmp_path / "bbq-alltypes-questions.txt"
	with open(bbq_file, "w", encoding="utf-8") as f:
		for line in sample_bbq_lines:
			f.write(line + "\n")

	argv = [
		sys.executable,
		converter,
		"-i",
		str(bbq_file),
		"--all",
		"--allow-mixed",
		"--quiet",
	]
	env = os.environ.copy()
	env["PYTHONPATH"] = repo_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

	result = subprocess.run(
		argv,
		cwd=str(tmp_path),
		env=env,
		check=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)

	if result.stdout:
		print(result.stdout.strip())

	required_outputs = [
		tmp_path / "qti21-alltypes.zip",
		tmp_path / "human-alltypes.html",
		tmp_path / "bbq-alltypes.txt",
		tmp_path / "selftest-alltypes.html",
	]

	for outpath in required_outputs:
		assert_exists_and_nonempty(str(outpath))

	assert_zip_has_manifest(str(tmp_path / "qti21-alltypes.zip"))

	optional_qti12 = tmp_path / "qti12-alltypes.zip"
	if optional_qti12.exists():
		assert_exists_and_nonempty(str(optional_qti12))
		assert_zip_has_manifest(str(optional_qti12))
