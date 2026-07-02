"""
Cross-engine end-to-end coverage for the image-support plan, matrix
rows 8, 9, 11, 12, 13.

Every per-engine media unit test (tests/unit/test_*_media.py) and the
existing tests/integration/test_qti_writer_media.py and
tests/integration/test_blackboard_export_zip_read_media.py already prove each
engine's media behavior in isolation, against a bank built directly in the
test. This module proves the layer those tests do not: a real READER feeding
a real WRITER (or the same bank fanning out across several writers), so the
seam between the two is exercised, not just each side alone.

A genuine production
bug found while writing row 8/9 (QTIPackageInterface.read_package() dropped the
reader's media_base_dir) has since been fixed (ItemBank.merge() now carries
media_base_dir forward), and
tests/integration/test_package_interface_media_read.py is a passing regression
test for it; that is why the chains below drive readers and writers directly
rather than through package_interface.read_package().
"""

# Standard Library
import os
import base64
import pathlib
import zipfile

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker import package_interface
from qti_package_maker.common import media_assets
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines.bbq_text_upload import read_package as bbq_read_package
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as canvas_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import engine_class as bb_qti21_engine
from qti_package_maker.engines.blackboard_export_zip import engine_class as bbexport_engine
from qti_package_maker.engines.blackboard_export_zip import read_package as bbexport_read_package
from qti_package_maker.engines.blackboard_export_zip import assessment_meta
from qti_package_maker.engines.html_selftest import engine_class as html_selftest_engine

import file_utils

# 1x1 transparent PNG, 68 bytes. Inline per the PYTEST_STYLE fixture policy
# (reused from tests/unit/test_media_assets.py's constant pattern).
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# 1x1 transparent GIF, 34 bytes.
GIF_BYTES = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")

FIXTURE_ZIP = os.path.join(
	file_utils.get_repo_root(), "tests", "fixtures", "bb_export_slice.zip")


#========================================================
# Row 8: BBQ .txt with a relative img + sibling dir (built in tmp_path) reads
# cleanly, then feeds each packaging engine end to end.
#========================================================
def _write_bbq_with_image(tmp_path: pathlib.Path) -> pathlib.Path:
	"""Write a one-item BBQ text file whose question references a relative image."""
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	bbq_file = tmp_path / "bbq-with-image.txt"
	question = '<p>See figure</p><img src="images/figure.png" alt="fig"/>'
	bbq_file.write_text(f"MC\t{question}\t3\tincorrect\t4\tcorrect\n", encoding="utf-8")
	return bbq_file


#============================================
def test_bbq_reader_feeds_canvas_writer_end_to_end(tmp_cwd: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_cwd)
	bank = bbq_read_package.read_items_from_file(str(bbq_file))
	# reader sets media_base_dir purely by derivation; src resolves
	assert bank.media_base_dir == str(tmp_cwd)

	engine = canvas_engine.EngineClass("chain-canvas", verbose=False)
	outfile = tmp_cwd / "chain_canvas.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = set(zip_file.namelist())
		assert "media/figure.png" in names
		assert zip_file.read("media/figure.png") == PNG_BYTES
		items_text = zip_file.read("canvas_qti12_questions/canvas_qti12_questions.xml").decode("utf-8")
		# src rewritten to Canvas's platform-relative form
		assert 'src="../media/figure.png"' in items_text
		manifest_text = zip_file.read("imsmanifest.xml").decode("utf-8")
		assert 'type="webcontent"' in manifest_text


#============================================
def test_bbq_reader_feeds_blackboard_qti21_writer_end_to_end(tmp_cwd: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_cwd)
	bank = bbq_read_package.read_items_from_file(str(bbq_file))

	engine = bb_qti21_engine.EngineClass("chain-bbqti21", verbose=False)
	outfile = tmp_cwd / "chain_bbqti21.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = set(zip_file.namelist())
		# BB QTI 2.1 places images at the package ROOT (SAMPLES-confirmed layout)
		assert "figure.png" in names
		assert zip_file.read("figure.png") == PNG_BYTES
		item_text = zip_file.read("qti21_items/item_00001.xml").decode("utf-8")
		assert 'src="../figure.png"' in item_text
		manifest_text = zip_file.read("imsmanifest.xml").decode("utf-8")
		assert 'type="webcontent"' in manifest_text


#============================================
def test_bbq_reader_feeds_blackboard_export_zip_writer_end_to_end(tmp_cwd: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_cwd)
	bank = bbq_read_package.read_items_from_file(str(bbq_file))

	engine = bbexport_engine.EngineClass("chain-bbexport", verbose=False)
	outfile = tmp_cwd / "chain_bbexport.zip"
	engine.save_package(bank, outfile=str(outfile))

	# a single local image gets the deterministic first xid
	expected_binary_name = assessment_meta.csfiles_binary_name(1, ".png")
	expected_body_token = assessment_meta.csfiles_src_value(1)
	expected_resource_id = assessment_meta.make_resource_id(1)
	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = set(zip_file.namelist())
		assert f"csfiles/home_dir/{expected_binary_name}" in names
		assert zip_file.read(f"csfiles/home_dir/{expected_binary_name}") == PNG_BYTES
		pool_text = zip_file.read(assessment_meta.POOL_DAT_FILENAME).decode("utf-8")
		# src rewritten to the csfiles bbcswebdav token (manifest/dat declaration)
		assert expected_body_token in pool_text
		links_text = zip_file.read(assessment_meta.CSRESOURCELINKS_DAT_FILENAME).decode("utf-8")
		assert f"<resourceId>{expected_resource_id}</resourceId>" in links_text

	# read back through the engine's own reader: bytes + reference recovered
	bank_b = bbexport_read_package.read_items_from_file(str(outfile), allow_mixed=True)
	mc_item = next(iter(bank_b))
	assert '<img src="figure.png"' in mc_item.question_text
	recovered_path = os.path.join(bank_b.media_base_dir, "figure.png")
	with open(recovered_path, "rb") as recovered_file:
		assert recovered_file.read() == PNG_BYTES


#========================================================
# Row 9: BB Original ZIP with a csfiles image (real-export). Reads the
# committed fixture slice, then proves write->read preserves both the bytes
# and the references through a SECOND write->read cycle, so the images stay
# byte-identical all the way back to the ORIGINAL fixture binaries (not just
# to the intermediate read).
#========================================================
def _read_fixture_bytes(*relative_parts: str) -> bytes:
	"""Read raw bytes of an entry from the committed fixture ZIP."""
	arcname = "/".join(relative_parts)
	with zipfile.ZipFile(FIXTURE_ZIP, "r") as zip_file:
		return zip_file.read(arcname)


#============================================
def test_real_export_write_read_roundtrip_preserves_bytes_and_refs(tmp_cwd: pathlib.Path) -> None:
	bank_a = bbexport_read_package.read_items_from_file(FIXTURE_ZIP, allow_mixed=True)
	mc_items_a = [item_cls for item_cls in bank_a if item_cls.item_type == "MC"]
	assert len(mc_items_a) == 1

	engine = bbexport_engine.EngineClass("real-export-roundtrip", verbose=False)
	outfile = tmp_cwd / "real_export_rewritten.zip"
	engine.save_package(bank_a, outfile=str(outfile))

	bank_b = bbexport_read_package.read_items_from_file(str(outfile), allow_mixed=True)
	mc_items_b = [item_cls for item_cls in bank_b if item_cls.item_type == "MC"]
	assert len(mc_items_b) == 1
	mc_item_b = mc_items_b[0]

	# References survive the second write->read cycle for all 5 MC-item images
	# (stem + 4 choices); order-insensitive since choice ordering is not the
	# behavior under test here (covered by test_blackboard_export_zip_roundtrip.py).
	combined_html_b = mc_item_b.question_text + " ".join(mc_item_b.choices_list)
	expected_by_recovered_name = {
		"image-1.jpg": "__xid-23446236_1.jpg",
		"image-2.jpg": "__xid-23446237_1.jpg",
		"image-3.jpg": "__xid-23446238_1.jpg",
		"image-4.jpg": "__xid-23446239_1.jpg",
		"image-5.jpg": "__xid-23446240_1.jpg",
	}
	for recovered_name in expected_by_recovered_name:
		assert f'<img src="{recovered_name}"' in combined_html_b
	assert "@X@EmbeddedFile.requestUrlStub@X@bbcswebdav" not in combined_html_b

	# Bytes stay byte-identical to the ORIGINAL (downsized) fixture binaries,
	# not merely to the intermediate read.
	for recovered_name, fixture_basename in expected_by_recovered_name.items():
		recovered_path = os.path.join(bank_b.media_base_dir, recovered_name)
		with open(recovered_path, "rb") as recovered_file:
			recovered_bytes = recovered_file.read()
		expected_bytes = _read_fixture_bytes("csfiles", "home_dir", fixture_basename)
		assert recovered_bytes == expected_bytes


#========================================================
# Row 11: html_selftest with multiple images -- every src is a data: URI,
# zero external refs. Complements (does not duplicate)
# tests/unit/test_html_selftest_media.py, which proves a single image; this
# uses media_assets.scan_html_for_assets (the plan's own scanning tool) to
# comprehensively confirm every <img src> in the emitted fragment, not just
# the one image checked in the unit test.
#========================================================
def test_html_selftest_multi_image_every_src_is_data_uri(tmp_path: pathlib.Path) -> None:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "first.png").write_bytes(PNG_BYTES)
	(image_dir / "second.gif").write_bytes(GIF_BYTES)
	bank = item_bank.ItemBank(media_base_dir=str(tmp_path))
	bank.add_item("MC", (
		'<p>See <img src="images/first.png" alt="one"/></p>',
		['<img src="images/second.gif" alt="two"/> Choice A', "Choice B"],
		"Choice B",
	))
	engine = html_selftest_engine.EngineClass("row11-multi", verbose=False)
	outfile = str(tmp_path / "selftest-multi.html")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")

	found_srcs = media_assets.scan_html_for_assets(written_text)
	assert len(found_srcs) == 2
	assert all(src.startswith("data:image/") for src in found_srcs)


#========================================================
# Row 12: no-image bank through every packaging engine -- behavior-identical
# (no media artifacts appear). Complements the pre-existing no-image outputs
# in tests/integration/test_engine_outputs.py (which assert basic content
# survives) by asserting the NEW media plumbing this plan added is a true
# no-op for image-free content.
#========================================================
def _make_no_image_bank() -> item_bank.ItemBank:
	bank = item_bank.ItemBank()
	bank.add_item("MC", ("Plain question, no images.", ["A", "B"], "A"))
	return bank


#============================================
def test_no_image_bank_collect_assets_is_empty() -> None:
	bank = _make_no_image_bank()
	collected = bank.collect_assets()
	assert collected.assets == []
	assert collected.item_dependencies == {}


#============================================
def test_canvas_no_image_output_has_no_media_artifacts(tmp_cwd: pathlib.Path) -> None:
	bank = _make_no_image_bank()
	engine = canvas_engine.EngineClass("row12-canvas", verbose=False)
	outfile = tmp_cwd / "row12_canvas.zip"
	engine.save_package(bank, outfile=str(outfile))
	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = zip_file.namelist()
		assert not any(name.startswith("media/") for name in names)
		manifest_text = zip_file.read("imsmanifest.xml").decode("utf-8")
		assert "webcontent" not in manifest_text


#============================================
def test_blackboard_qti21_no_image_output_has_no_media_artifacts(tmp_cwd: pathlib.Path) -> None:
	bank = _make_no_image_bank()
	engine = bb_qti21_engine.EngineClass("row12-bbqti21", verbose=False)
	outfile = tmp_cwd / "row12_bbqti21.zip"
	engine.save_package(bank, outfile=str(outfile))
	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = zip_file.namelist()
		assert not any(name.endswith((".png", ".jpg", ".jpeg", ".gif")) for name in names)
		manifest_text = zip_file.read("imsmanifest.xml").decode("utf-8")
		assert "webcontent" not in manifest_text


#============================================
def test_blackboard_export_zip_no_image_output_has_no_csfiles_binaries(tmp_cwd: pathlib.Path) -> None:
	bank = _make_no_image_bank()
	engine = bbexport_engine.EngineClass("row12-bbexport", verbose=False)
	outfile = tmp_cwd / "row12_bbexport.zip"
	engine.save_package(bank, outfile=str(outfile))
	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = zip_file.namelist()
		# historical no-image layout: csfiles/ ships as an empty-dir marker only
		assert not any(name.startswith("csfiles/home_dir/") for name in names)
		assert "csfiles/" in names
		links_text = zip_file.read(assessment_meta.CSRESOURCELINKS_DAT_FILENAME).decode("utf-8")
		assert "<cms_resource_link>" not in links_text


#========================================================
# Row 13: one shared image item -> reference engines (bbq, human_readable,
# text2qti, exam_yaml) keep a traceable path reference + warn, vs placeholder
# engines (moodle_aiken, okla_chrst_bqgen) emit a bare `[image: name.ext]`
# placeholder + warn. Each engine's exact output syntax is already pinned by
# its own tests/unit/test_*_media.py; this proves the CLASS-LEVEL distinction
# (traceable path retained vs bare placeholder) holds consistently across the
# whole declared set from ONE shared item, driven through package_interface
# (the user-facing entry point; safe here since no read is involved).
#========================================================
REFERENCE_ENGINES = ("bbq_text_upload", "human_readable", "text2qti", "exam_yaml")
PLACEHOLDER_ENGINES = ("moodle_aiken", "okla_chrst_bqgen")


#============================================
def _build_packer_with_image(tmp_cwd: pathlib.Path) -> package_interface.QTIPackageInterface:
	image_dir = tmp_cwd / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	qti = package_interface.QTIPackageInterface("row13", verbose=False)
	# directly-assigned media_base_dir is a caller-owned, sanctioned pattern
	# (see ItemBank.cleanup()'s ownership rule); no read is involved here.
	qti.item_bank.media_base_dir = str(tmp_cwd)
	qti.add_item("MC", (
		'<p>See figure</p><img src="images/figure.png" alt="fig"/>',
		["A", "B"],
		"A",
	))
	return qti


#============================================
@pytest.mark.parametrize("engine_name", REFERENCE_ENGINES)
def test_reference_engines_retain_traceable_path_and_warn(
			tmp_cwd: pathlib.Path, engine_name: str, capsys: pytest.CaptureFixture) -> None:
	qti = _build_packer_with_image(tmp_cwd)
	outfile = qti.save_package(engine_name)
	assert outfile
	output_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "figure.png" in output_text
	# a traceable path survives (verbatim <img src>, markdown ref, or "source: ...")
	assert ("images/figure.png" in output_text) or ("media/figure.png" in output_text)
	warning_output = capsys.readouterr().out
	assert "images/figure.png" in warning_output


#============================================
@pytest.mark.parametrize("engine_name", PLACEHOLDER_ENGINES)
def test_placeholder_engines_emit_bare_placeholder_and_warn(
			tmp_cwd: pathlib.Path, engine_name: str, capsys: pytest.CaptureFixture) -> None:
	qti = _build_packer_with_image(tmp_cwd)
	outfile = qti.save_package(engine_name)
	assert outfile
	output_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "[image: figure.png]" in output_text
	assert "<img" not in output_text
	# no traceable path survives; only the bare basename placeholder
	assert "images/figure.png" not in output_text
	warning_output = capsys.readouterr().out
	assert "images/figure.png" in warning_output
