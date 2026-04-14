# Standard Library
import os
import sys
import subprocess

# Pip3 Library
import pytest


def test_bbq_converter_rejects_bad_filename(tmp_path):
	repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	converter = os.path.join(repo_root, "tools", "bbq_converter.py")

	bad_file = tmp_path / "bad-questions.txt"
	bad_file.write_text("MC\t2+2?\t3\tincorrect\t4\tcorrect\n", encoding="utf-8")

	argv = [
		sys.executable,
		converter,
		"-i",
		str(bad_file),
		"-1",
	]
	env = os.environ.copy()
	env["PYTHONPATH"] = repo_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

	with pytest.raises(subprocess.CalledProcessError) as excinfo:
		subprocess.run(
			argv,
			cwd=str(tmp_path),
			env=env,
			check=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
		)

	assert "does not match expected pattern" in excinfo.value.stdout


def test_bbq_converter_ultra_flag(tmp_path):
	"""Test that the --ultra flag produces a valid output ZIP."""
	repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	converter = os.path.join(repo_root, "tools", "bbq_converter.py")

	# Create a minimal BBQ file with 1 MC question
	bbq_file = tmp_path / "bbq-test_ultra-questions.txt"
	bbq_file.write_text("MC\tWhat is 2+2?\t3\tincorrect\t4\tcorrect\n", encoding="utf-8")

	argv = [
		sys.executable,
		converter,
		"-i",
		str(bbq_file),
		"-u",
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

	# Verify the output ZIP exists
	output_zip = tmp_path / "qti21-ultra-test_ultra.zip"
	assert output_zip.exists(), f"Expected output ZIP {output_zip.name} not found. Output:\n{result.stdout}"
