"""
Engine smoke tests for the blackboard_export_zip write path (WP-W1).

Exercises the full EngineClass.save_package pipeline end-to-end:
  - The ZIP contains no .bb-package-sig (server-side only).
  - An ORDER item emits a warning (via base_engine dispatch) and is absent from
    the pool.

The basic "writes a valid ZIP with manifest + pool dat" path is covered by the
round-trip test, which writes via the engine and reads the result back.

These tests write only inside tmp_path and finish well under a second.
"""

# Standard Library
import zipfile

# QTI Package Maker
from qti_package_maker.package_interface import QTIPackageInterface


#============================================
def test_save_package_omits_bb_package_sig(tmp_path):
	"""
	save_package must NOT include .bb-package-sig (server-computed, omission is correct).
	"""
	outfile = str(tmp_path / "out.zip")
	qti = QTIPackageInterface(
		package_name="test_bb_sig",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("MC", (
		"What is 2+2?",
		["3", "4", "5"],
		"4",
	))
	result = qti.save_package("blackboard_export_zip", outfile)

	with zipfile.ZipFile(result, "r") as z:
		names = z.namelist()
	assert ".bb-package-sig" not in names


#============================================
def test_order_item_produces_warning_and_is_absent(tmp_path, capsys):
	"""
	An ORDER item causes a base_engine warning and does not appear in the pool dat.
	"""
	outfile = str(tmp_path / "out.zip")
	qti = QTIPackageInterface(
		package_name="test_bb_order",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("MC", (
		"What color is the sky?",
		["blue", "red", "green"],
		"blue",
	))
	qti.add_item("ORDER", (
		"Rank these by size.",
		["small", "medium", "large"],
	))
	result = qti.save_package("blackboard_export_zip", outfile)

	# The base_engine warning should mention ORDER
	captured = capsys.readouterr()
	assert "ORDER" in captured.out

	# Pool dat should contain the MC item and no ORDER item.
	with zipfile.ZipFile(result, "r") as z:
		pool_text = z.read("res00002.dat").decode("utf-8")
	# The supported MC item's question text is present in the pool.
	assert "What color is the sky?" in pool_text
	# ORDER items are not serialized by this engine; no ORDER marker should appear.
	assert "ORDER" not in pool_text
