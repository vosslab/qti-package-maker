"""
Regression tests: a rejected media bank must not leak a staging directory.

Every file-packaging engine builds its ZIP from a timestamped staging directory
created in the current working directory. A data-URI image cannot be packaged as
a file, so save_package raises media_assets.MediaPolicyError. These tests pin the
fix that validates media policy BEFORE the staging directory is created, so a
rejected bank leaves the working directory clean (no leaked staging dir).

Each test runs inside tmp_path via monkeypatch.chdir so it is hermetic and a
real leak would show up as a stray directory in the temp cwd.
"""

# Standard Library
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as qti12_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import engine_class as qti21_engine
from qti_package_maker.engines.blackboard_export_zip import engine_class as bb_export_engine


#============================================
def _build_data_uri_bank(tmp_path: pathlib.Path) -> ItemBank:
	"""
	Build a one-item bank whose only image is an unpackagable data URI.
	"""
	encoded = base64.b64encode(b"not a real gif").decode("ascii")
	bank = ItemBank(media_base_dir=str(tmp_path))
	bank.add_item("MC", (
		f'What does <img src="data:image/gif;base64,{encoded}" alt="fig"/> show?',
		["A", "B"],
		"A",
	))
	return bank


#============================================
def _cwd_entries(cwd: pathlib.Path) -> set:
	"""
	Return the set of directory names currently present in cwd.
	"""
	return {child.name for child in cwd.iterdir() if child.is_dir()}


#============================================
@pytest.mark.parametrize("engine_module", [
	qti12_engine,
	qti21_engine,
	bb_export_engine,
])
def test_data_uri_bank_raises_without_leaking_staging_dir(
			engine_module: object,
			tmp_path: pathlib.Path,
			monkeypatch: pytest.MonkeyPatch) -> None:
	"""
	A data-URI bank must raise MediaPolicyError and create no staging directory.
	"""
	monkeypatch.chdir(tmp_path)
	bank = _build_data_uri_bank(tmp_path)
	# Record the cwd directory listing before the failed save.
	dirs_before = _cwd_entries(tmp_path)
	engine = engine_module.EngineClass("leak-check", verbose=False)
	with pytest.raises(media_assets.MediaPolicyError, match="data URI"):
		engine.save_package(bank, outfile=str(tmp_path / "out.zip"))
	# The failed save must not have created any new directory in the cwd.
	dirs_after = _cwd_entries(tmp_path)
	assert dirs_after == dirs_before
