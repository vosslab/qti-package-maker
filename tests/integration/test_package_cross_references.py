# Standard Library
import os
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
import file_utils
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.common import package_integrity
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as canvas_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import engine_class as bb_qti21_engine
from qti_package_maker.engines.blackboard_export_zip import engine_class as bb_export_engine


REPO_ROOT = file_utils.get_repo_root()

# An 8x8 solid-color PNG used as the single embedded image in the
# representative bank. Must clear package_integrity.MIN_IMAGE_DIMENSION_PX
# (5px) so this fixture itself does not trip the image-dimension check; a
# 1x1 PNG lives below instead, as the canary that proves that check fires.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGNkaPjPgA0wYRUdtBIALlIBjzTK6JgAAAAASUVORK5CYII="
)

# Tiny 1x1-pixel raster constants for the image-dimension canary tests below.
# Same bytes as tests/unit/test_media_assets.py's PNG_BYTES/GIF_BYTES/
# JPEG_BYTES; duplicated locally so this module stays import-independent.
TINY_PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
TINY_GIF_BYTES = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")
TINY_JPEG_BYTES = base64.b64decode(
	"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
	"HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy"
	"MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIA"
	"AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
	"AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
	"ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
	"p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
	"AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
	"BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
	"U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
	"uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDi6KKK"
	"+ZP3E//Z"
)


#============================================
def _build_representative_bank() -> item_bank.ItemBank:
	"""
	Build a mixed bank exercising every answer-linkage shape plus one image.

	MC and MA cover single/multiple choice identifiers, MATCH covers directed
	pairs, NUM and FIB cover literal-answer responses, and the MC stem embeds
	one image so the media-src check has something to resolve.
	"""
	bank = item_bank.ItemBank(allow_mixed=True)
	# spill the image bytes so the MC stem's <img src> resolves like a real file
	bank.add_image("images/figure.png", PNG_BYTES)
	bank.add_item("MC", (
		'What color is <img src="images/figure.png" alt="fig"/> the sky?',
		["green", "blue", "red"],
		"blue",
	))
	bank.add_item("MA", (
		"Which are fruit?",
		["orange", "banana", "apple", "lettuce", "spinach"],
		["orange", "banana", "apple"],
	))
	bank.add_item("MATCH", (
		"Match item to color.",
		["orange", "banana", "lettuce"],
		["orange", "yellow", "green"],
	))
	bank.add_item("NUM", ("What is 2 + 2?", 4.0, 0.1, True))
	bank.add_item("FIB", ("Complete the sentence: The sky is __.", ["blue"]))
	# engines assume renumbered items, matching the package_interface flow
	bank.renumber_items()
	return bank


#============================================
def _make_canvas_relative(package_name: str) -> canvas_engine.EngineClass:
	return canvas_engine.EngineClass(package_name, verbose=False)


#============================================
def _make_canvas_filebase(package_name: str) -> canvas_engine.EngineClass:
	return canvas_engine.EngineClass(
		package_name, verbose=False,
		canvas_src_variant=canvas_engine.CANVAS_SRC_VARIANT_FILEBASE)


#============================================
def _make_bb_qti21(package_name: str) -> bb_qti21_engine.EngineClass:
	return bb_qti21_engine.EngineClass(package_name, verbose=False)


#============================================
def _make_bb_export(package_name: str) -> bb_export_engine.EngineClass:
	return bb_export_engine.EngineClass(package_name, verbose=False)


# The packaging matrix: a human label mapped to an engine factory. Canvas
# appears twice because its two <img src> variants rewrite media differently.
ENGINE_FACTORIES = {
	"canvas_qti_v1_2_relative": _make_canvas_relative,
	"canvas_qti_v1_2_filebase": _make_canvas_filebase,
	"blackboard_qti_v2_1": _make_bb_qti21,
	"blackboard_export_zip": _make_bb_export,
}


#============================================
@pytest.mark.parametrize("engine_label", sorted(ENGINE_FACTORIES.keys()))
def test_packaging_engine_output_is_cross_reference_clean(
			engine_label: str, tmp_path: pathlib.Path) -> None:
	"""
	Every packaging engine must emit a package with no dangling references.

	This also serves as the green-path proof for the QTI 2.1 SCORE
	outcomeDeclaration check (only blackboard_qti_v2_1 emits assessmentItem
	entries, and item_xml_helpers.create_outcome_declarations() always
	includes SCORE), since violations == [] covers every check
	check_package runs, including that new check.
	"""
	bank = _build_representative_bank()
	engine = ENGINE_FACTORIES[engine_label]("xref-check")
	outfile = tmp_path / f"{engine_label}.zip"
	engine.save_package(bank, outfile=str(outfile))
	violations = package_integrity.check_package(str(outfile))
	assert violations == [], f"{engine_label} produced integrity violations: {violations}"


#============================================
def test_committed_bb_export_fixture_is_clean() -> None:
	"""The committed real-shape Blackboard export slice must pass the check."""
	fixture_zip = os.path.join(REPO_ROOT, "tests", "fixtures", "bb_export_slice.zip")
	violations = package_integrity.check_package(fixture_zip)
	assert violations == [], f"bb_export_slice fixture has integrity violations: {violations}"


# ---------------------------------------------------------------------------
# Regression canaries: minimal packages built in-test that reproduce the two
# original Blackboard import failures plus the generic manifest failure. Each
# proves the check DETECTS the bug class, not just that clean packages pass.
# ---------------------------------------------------------------------------


#============================================
def test_canary_qti21_correctresponse_id_mismatch_is_flagged() -> None:
	"""
	Reproduce original bug 1: a QTI 2.1 correctResponse names answer_002 while
	the choices are answer_1..N. The check must flag the dangling identifier.
	"""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\" identifier=\"m\">"
		b"<resources>"
		b"<resource href=\"qti21_items/item_00001.xml\" identifier=\"item_00001\""
		b" type=\"imsqti_item_xmlv2p1\">"
		b"<file href=\"qti21_items/item_00001.xml\"/>"
		b"</resource></resources></manifest>"
	)
	item = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<assessmentItem xmlns=\"http://www.imsglobal.org/xsd/imsqti_v2p1\""
		b" identifier=\"brk1\">"
		b"<responseDeclaration baseType=\"identifier\" cardinality=\"single\""
		b" identifier=\"RESPONSE\">"
		b"<correctResponse><value>answer_002</value></correctResponse>"
		b"</responseDeclaration>"
		b"<itemBody><choiceInteraction responseIdentifier=\"RESPONSE\" maxChoices=\"1\">"
		b"<simpleChoice identifier=\"answer_1\"><p>a</p></simpleChoice>"
		b"<simpleChoice identifier=\"answer_2\"><p>b</p></simpleChoice>"
		b"</choiceInteraction></itemBody></assessmentItem>"
	)
	entries = {"imsmanifest.xml": manifest, "qti21_items/item_00001.xml": item}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a QTI 2.1 correctResponse id mismatch"
	assert any("answer_002" in v for v in violations)


#============================================
def test_canary_bb_export_parentid_mismatch_is_flagged() -> None:
	"""
	Reproduce original bug 2: a CSResourceLinks parentId names an ASI object id
	that no pool item emitted. The check must flag the dangling parentId.
	"""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns:bb=\"http://www.blackboard.com/content-packaging/\""
		b" identifier=\"man\"><resources>"
		b"<resource bb:file=\"res00002.dat\" identifier=\"res00002\""
		b" type=\"assessment/x-bb-qti-pool\" xml:base=\"res00002\"/>"
		b"<resource bb:file=\"res00005.dat\" identifier=\"res00005\""
		b" type=\"course/x-bb-csresourcelinks\" xml:base=\"res00005\"/>"
		b"</resources></manifest>"
	)
	pool = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<questestinterop><assessment><section><item><itemmetadata>"
		b"<bbmd_asi_object_id>_111_1</bbmd_asi_object_id>"
		b"</itemmetadata></item></section></assessment></questestinterop>"
	)
	links = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<cms_resource_link_list><cms_resource_link>"
		b"<parentId parent_data_type=\"asiobject\">_999_9</parentId>"
		b"<resourceId>5_1</resourceId>"
		b"</cms_resource_link></cms_resource_link_list>"
	)
	entries = {"imsmanifest.xml": manifest, "res00002.dat": pool, "res00005.dat": links}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a bb-export parentId mismatch"
	assert any("_999_9" in v for v in violations)


#============================================
def test_canary_qti12_varequal_id_mismatch_is_flagged() -> None:
	"""A QTI 1.2 scored varequal into a choice response with no such label."""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\" identifier=\"m\">"
		b"<resources><resource href=\"q.xml\" identifier=\"q\""
		b" type=\"imsqti_xmlv1p2\"><file href=\"q.xml\"/></resource></resources></manifest>"
	)
	questions = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<questestinterop xmlns=\"http://www.imsglobal.org/xsd/ims_qtiasiv1p2\">"
		b"<assessment><section><item ident=\"mc1\"><presentation>"
		b"<response_lid ident=\"response1\"><render_choice>"
		b"<response_label ident=\"choice_001\"><material><mattext>a</mattext></material></response_label>"
		b"<response_label ident=\"choice_002\"><material><mattext>b</mattext></material></response_label>"
		b"</render_choice></response_lid></presentation>"
		b"<resprocessing><respcondition><conditionvar>"
		b"<varequal respident=\"response1\">choice_999</varequal>"
		b"</conditionvar></respcondition></resprocessing>"
		b"</item></section></assessment></questestinterop>"
	)
	entries = {"imsmanifest.xml": manifest, "q.xml": questions}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a QTI 1.2 varequal id mismatch"
	assert any("choice_999" in v for v in violations)


#============================================
def test_canary_manifest_and_media_dangling_are_flagged() -> None:
	"""A dangling <file href>, dependency identifierref, and <img src> all flag."""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\" identifier=\"m\">"
		b"<resources><resource href=\"item.xml\" identifier=\"item\""
		b" type=\"imsqti_item_xmlv2p1\"><file href=\"item.xml\"/>"
		b"<file href=\"ghost.xml\"/><dependency identifierref=\"nope\"/>"
		b"</resource></resources></manifest>"
	)
	item = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<assessmentItem xmlns=\"http://www.imsglobal.org/xsd/imsqti_v2p1\""
		b" identifier=\"it\"><itemBody><div>See"
		b" <img src=\"../missing.png\"/></div></itemBody></assessmentItem>"
	)
	entries = {"imsmanifest.xml": manifest, "item.xml": item}
	violations = package_integrity.check_entries(entries)
	assert any("ghost.xml" in v for v in violations)
	assert any("nope" in v for v in violations)
	assert any("missing.png" in v for v in violations)


# A bare manifest with no resources, used by the standalone image-dimension
# and identifier-safety canaries below so each test isolates one bug class.
_MINIMAL_MANIFEST = (
	b"<?xml version='1.0' encoding='UTF-8'?>"
	b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\" identifier=\"m\">"
	b"<resources></resources></manifest>"
)


#============================================
def test_canary_one_pixel_png_dimension_is_flagged() -> None:
	"""
	Reproduce the live incident: a 1x1 PNG probe imported into Blackboard
	cleanly but was invisible on the rendered page. The check must flag it.
	"""
	entries = {"imsmanifest.xml": _MINIMAL_MANIFEST, "images/probe.png": TINY_PNG_BYTES}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a 1x1 PNG"
	assert any("images/probe.png" in v and "1x1" in v for v in violations)


#============================================
def test_canary_one_pixel_gif_dimension_is_flagged() -> None:
	"""A 1x1 GIF is the same invisible-pixel bug class as the PNG probe."""
	entries = {"imsmanifest.xml": _MINIMAL_MANIFEST, "images/probe.gif": TINY_GIF_BYTES}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a 1x1 GIF"
	assert any("images/probe.gif" in v and "1x1" in v for v in violations)


#============================================
def test_canary_one_pixel_jpeg_dimension_is_flagged() -> None:
	"""A 1x1 JPEG is the same invisible-pixel bug class as the PNG probe."""
	entries = {"imsmanifest.xml": _MINIMAL_MANIFEST, "images/probe.jpg": TINY_JPEG_BYTES}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a 1x1 JPEG"
	assert any("images/probe.jpg" in v and "1x1" in v for v in violations)


#============================================
def test_canary_corrupt_image_header_is_flagged() -> None:
	"""An extension that names a raster format but an unparsable header flags too."""
	entries = {"imsmanifest.xml": _MINIMAL_MANIFEST, "images/broken.png": b"not a png"}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag an unreadable image header"
	assert any("images/broken.png" in v for v in violations)


#============================================
def test_canary_manifest_identifier_with_space_is_flagged() -> None:
	"""
	Reproduce a real bug shipped in our own output: a manifest identifier
	containing a literal space (identifier="main manifest") is not an
	id-safe token and must be flagged.
	"""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\""
		b" identifier=\"main manifest\"><resources></resources></manifest>"
	)
	entries = {"imsmanifest.xml": manifest}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a manifest identifier containing a space"
	assert any("main manifest" in v for v in violations)


#============================================
def test_canary_resource_identifier_with_space_is_flagged() -> None:
	"""A <resource identifier> containing a space must also be flagged."""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\" identifier=\"m\">"
		b"<resources><resource href=\"item.xml\" identifier=\"bad id\""
		b" type=\"imsqti_item_xmlv2p1\"><file href=\"item.xml\"/></resource>"
		b"</resources></manifest>"
	)
	item = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<assessmentItem xmlns=\"http://www.imsglobal.org/xsd/imsqti_v2p1\""
		b" identifier=\"it\"><itemBody/></assessmentItem>"
	)
	entries = {"imsmanifest.xml": manifest, "item.xml": item}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a resource identifier containing a space"
	assert any("bad id" in v for v in violations)


#============================================
def test_canary_item_ident_leading_digit_is_flagged() -> None:
	"""A QTI 1.2 <item ident> that starts with a digit is not an id-safe token."""
	manifest = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<manifest xmlns=\"http://www.imsglobal.org/xsd/imscp_v1p1\" identifier=\"m\">"
		b"<resources><resource href=\"q.xml\" identifier=\"q\""
		b" type=\"imsqti_xmlv1p2\"><file href=\"q.xml\"/></resource></resources></manifest>"
	)
	questions = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<questestinterop xmlns=\"http://www.imsglobal.org/xsd/ims_qtiasiv1p2\">"
		b"<assessment><section><item ident=\"1mc\"><presentation/>"
		b"</item></section></assessment></questestinterop>"
	)
	entries = {"imsmanifest.xml": manifest, "q.xml": questions}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag an item ident starting with a digit"
	assert any("1mc" in v for v in violations)


#============================================
def test_canary_qti21_item_missing_score_outcome_is_flagged() -> None:
	"""A QTI 2.1 assessmentItem with no outcomeDeclaration identifier=SCORE."""
	item = (
		b"<?xml version='1.0' encoding='UTF-8'?>"
		b"<assessmentItem xmlns=\"http://www.imsglobal.org/xsd/imsqti_v2p1\""
		b" identifier=\"noscore\"><itemBody/></assessmentItem>"
	)
	entries = {"imsmanifest.xml": _MINIMAL_MANIFEST, "item.xml": item}
	violations = package_integrity.check_entries(entries)
	assert violations, "check failed to flag a QTI 2.1 item missing SCORE outcomeDeclaration"
	assert any("noscore" in v and "SCORE" in v for v in violations)
