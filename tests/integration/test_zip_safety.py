# Standard Library
import os
import zipfile
import pathlib

# QTI Package Maker
import qti_package_maker.package_interface


def _make_packer() -> qti_package_maker.package_interface.QTIPackageInterface:
	qti_packer = qti_package_maker.package_interface.QTIPackageInterface("zip-safe", verbose=False, allow_mixed=True)
	qti_packer.add_item("MC", ("What is 2 + 2?", ["3", "4"], "4"))
	return qti_packer


def _assert_zip_safe(zip_path: str) -> None:
	with zipfile.ZipFile(zip_path, "r") as zf:
		for name in zf.namelist():
			assert not os.path.isabs(name)
			parts = pathlib.PurePosixPath(name).parts
			assert ".." not in parts


def test_qti12_zip_paths_safe(tmp_cwd: pathlib.Path) -> None:
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("canvas_qti_v1_2")
	_assert_zip_safe(outfile)


def test_qti21_zip_paths_safe(tmp_cwd: pathlib.Path) -> None:
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("blackboard_qti_v2_1")
	_assert_zip_safe(outfile)
