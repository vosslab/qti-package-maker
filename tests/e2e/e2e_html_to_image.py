#!/usr/bin/env python3
"""CLI: --html-to-image writes PNG-bearing Blackboard packages."""

# Standard Library
import os
import sys
import glob
import zipfile
import subprocess

_TESTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _TESTS_DIR not in sys.path:
	sys.path.insert(0, _TESTS_DIR)
if _REPO_ROOT not in sys.path:
	sys.path.insert(0, _REPO_ROOT)

# local repo modules
import file_utils
from qti_package_maker.common import package_integrity


PNG_MAGIC = b"\x89PNG"
REPO_ROOT = file_utils.get_repo_root()
CONVERTER = os.path.join(REPO_ROOT, "tools", "bbq_converter.py")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output_smoke", "html_to_image")

DRAWING_TABLE = (
	'<table><tr>'
	'<td bgcolor="#000000" style="border-top: 4px solid #111111; width: 80px; height: 80px;"></td>'
	'<td bgcolor="#eeeeee" style="border-top: 4px solid #333333; width: 80px; height: 80px;"></td>'
	"</tr></table>"
)


#============================================
def write_bbq(path: str) -> None:
	question = f"<p>Which lane matches?</p>{DRAWING_TABLE}"
	line = f"MC\t{question}\tlane A\tcorrect\tlane B\tincorrect\n"
	with open(path, "w", encoding="ascii") as handle:
		handle.write(line)


#============================================
def main() -> None:
	os.makedirs(OUTPUT_DIR, exist_ok=True)
	bbq_path = os.path.join(OUTPUT_DIR, "bbq-html_to_image-questions.txt")
	write_bbq(bbq_path)
	work_dir = os.path.join(OUTPUT_DIR, "cli_run")
	os.makedirs(work_dir, exist_ok=True)
	for zip_path in glob.glob(os.path.join(work_dir, "*.zip")):
		os.remove(zip_path)
	env = os.environ.copy()
	pythonpath = REPO_ROOT
	if env.get("PYTHONPATH"):
		pythonpath = REPO_ROOT + os.pathsep + env["PYTHONPATH"]
	env["PYTHONPATH"] = pythonpath
	argv = [
		sys.executable, CONVERTER, "-i", bbq_path,
		"-B", "-2", "--html-to-image",
	]
	result = subprocess.run(
		argv,
		cwd=work_dir,
		env=env,
		check=False,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)
	sys.stdout.write(result.stdout)
	if result.returncode != 0:
		raise SystemExit(f"converter failed with {result.returncode}")
	zips = sorted(glob.glob(os.path.join(work_dir, "*.zip")))
	if len(zips) != 2:
		raise SystemExit(f"expected two ZIPs, found {zips}")
	for zip_path in zips:
		violations = package_integrity.check_package(zip_path)
		if violations:
			raise SystemExit(f"{zip_path}: {violations}")
		with zipfile.ZipFile(zip_path) as zf:
			pngs = [name for name in zf.namelist() if name.lower().endswith(".png")]
			if not pngs:
				raise SystemExit(f"{zip_path} has no PNG members")
			for name in pngs:
				data = zf.read(name)
				if not data.startswith(PNG_MAGIC):
					raise SystemExit(f"{name} is not a PNG")
		print(f"ok {os.path.basename(zip_path)} pngs={len(pngs)}")
	print("e2e_html_to_image: PASS")


if __name__ == "__main__":
	main()
