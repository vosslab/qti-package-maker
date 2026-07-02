"""
Image-capture read tests for the blackboard_export_zip reader.

Reads the committed `tests/fixtures/bb_export_slice.zip` real-export slice
directly through the public entry point, proving both image mechanisms end
to end: csfiles `@X@...xid-<n>_1` tokens embedded in an MC item's HTML
(question stem + all four choices), and a hotspot `<matapplication uri>`
file wired into a "Hot Spot" item that the dispatch table does not model (so
its two images are only ever proven by extraction, never by ItemBank
content -- see `tests/fixtures/bb_export_slice_README.md` and the module
docstring of `read_package.py`).

Byte assertions compare against the FIXTURE zip entries (which were
deliberately downsized from the real SAMPLES export), never SAMPLES bytes.
"""

# Standard Library
import os
import zipfile

# QTI Package Maker
from qti_package_maker.engines.blackboard_export_zip import read_package

import file_utils

FIXTURE_ZIP = os.path.join(
	file_utils.get_repo_root(), "tests", "fixtures", "bb_export_slice.zip")

#============================================
def _read_fixture_bytes(*relative_parts: str) -> bytes:
	"""
	Read raw bytes of an entry from the committed fixture ZIP.

	Args:
		relative_parts: POSIX path segments of the ZIP entry (joined with "/").

	Returns:
		The entry's raw bytes.
	"""
	arcname = "/".join(relative_parts)
	with zipfile.ZipFile(FIXTURE_ZIP, "r") as zip_file:
		return zip_file.read(arcname)

#============================================
# Tests
#============================================
#============================================
def test_mc_item_html_rewritten_to_recovered_filenames() -> None:
	# The MC item's stem and all four choices carry csfiles tokens; every one
	# must be rewritten to a plain relative <img src> under media_base_dir,
	# with the @X@ token gone from the recovered HTML.
	bank = read_package.read_items_from_file(FIXTURE_ZIP, allow_mixed=True)
	mc_items = [item_cls for item_cls in bank if item_cls.item_type == "MC"]
	assert len(mc_items) == 1
	mc_item = mc_items[0]
	assert "@X@EmbeddedFile.requestUrlStub@X@bbcswebdav" not in mc_item.question_text
	assert '<img src="image-1.jpg"' in mc_item.question_text
	recovered_choice_srcs = [
		'<img src="image-2.jpg"' in choice_html for choice_html in mc_item.choices_list
	]
	assert any(recovered_choice_srcs)
	for choice_html in mc_item.choices_list:
		assert "@X@EmbeddedFile.requestUrlStub@X@bbcswebdav" not in choice_html

#============================================
def test_media_base_dir_set_and_extracted_bytes_match_fixture() -> None:
	# The bank's media_base_dir must point at a directory holding the 5 csfiles
	# images with byte-identical content to the (downsized) fixture binaries.
	bank = read_package.read_items_from_file(FIXTURE_ZIP, allow_mixed=True)
	assert bank.media_base_dir is not None
	expected_by_recovered_name = {
		"image-1.jpg": "__xid-23446236_1.jpg",
		"image-2.jpg": "__xid-23446237_1.jpg",
		"image-3.jpg": "__xid-23446238_1.jpg",
		"image-4.jpg": "__xid-23446239_1.jpg",
		"image-5.jpg": "__xid-23446240_1.jpg",
	}
	for recovered_name, fixture_basename in expected_by_recovered_name.items():
		extracted_path = os.path.join(bank.media_base_dir, recovered_name)
		with open(extracted_path, "rb") as extracted_file:
			extracted_bytes = extracted_file.read()
		expected_bytes = _read_fixture_bytes("csfiles", "home_dir", fixture_basename)
		assert extracted_bytes == expected_bytes

#============================================
def test_read_bank_owns_extraction_dir_and_cleanup_removes_it() -> None:
	# Reading an image-bearing pool creates its own tempfile.mkdtemp()
	# extraction directory (quality-review finding 2); the returned
	# bank must own that directory so cleanup() actually removes it, rather
	# than leaking one directory per read.
	bank = read_package.read_items_from_file(FIXTURE_ZIP, allow_mixed=True)
	media_dir = bank.media_base_dir
	assert media_dir is not None
	assert os.path.isdir(media_dir)

	bank.cleanup()

	assert bank.media_base_dir is None
	assert not os.path.isdir(media_dir)

#============================================
def test_hotspot_item_skipped_but_both_its_images_extracted(capsys: object) -> None:
	# "Hot Spot" carries no item_types class, so the item itself is skipped
	# exactly as before (unchanged dispatch behavior) -- but its two
	# images (a csfiles stem image AND a manifest-tracked matapplication
	# hotspot file) are still resolved into media_base_dir, since extraction
	# runs pool-wide and does not depend on item-type dispatch succeeding.
	bank = read_package.read_items_from_file(FIXTURE_ZIP, allow_mixed=True)
	captured = capsys.readouterr()
	assert "Hot Spot" in captured.out
	item_types_present = {item_cls.item_type for item_cls in bank}
	assert "HOTSPOT" not in item_types_present
	# xid-23446440 (hotspot stem) recovers to image-29.jpg.
	stem_path = os.path.join(bank.media_base_dir, "image-29.jpg")
	with open(stem_path, "rb") as stem_file:
		stem_bytes = stem_file.read()
	assert stem_bytes == _read_fixture_bytes("csfiles", "home_dir", "__xid-23446440_1.jpg")
	# The matapplication file resolves from res00002/<hash>/image-30.jpg.
	matapp_path = os.path.join(bank.media_base_dir, "image-30.jpg")
	with open(matapp_path, "rb") as matapp_file:
		matapp_bytes = matapp_file.read()
	assert matapp_bytes == _read_fixture_bytes(
		"res00002", "1eee67ddd3bf4b03ae0a9d03c55cf48d", "image-30.jpg"
	)

#============================================
def test_repair_html_void_elements_lowercases_mixed_case_markup() -> None:
	# _repair_html_void_elements re-serializes through lxml.html to self-close
	# void elements, but the libxml2 parser also lowercases every element and
	# attribute name while it does so (quality-review finding 4: the prior
	# docstring overclaimed no attributes were altered). Pin that normalization
	# so a future docstring or behavior drift is caught here.
	mixed_case_html = '<STRONG>bold</STRONG> <IMG SRC="a.png">'
	repaired_html = read_package._repair_html_void_elements(mixed_case_html)
	assert "<strong>bold</strong>" in repaired_html
	assert '<img src="a.png"' in repaired_html
	assert "STRONG" not in repaired_html
	assert "IMG" not in repaired_html
	assert "SRC" not in repaired_html
