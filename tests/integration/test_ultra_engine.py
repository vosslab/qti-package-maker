"""Integration tests for the Blackboard Ultra QTI 2.1 engine."""

# Standard Library
import os
import zipfile

# Pip3 Library
import lxml.etree

# QTI Package Maker
import qti_package_maker.package_interface


NS = {"qti": "http://www.imsglobal.org/xsd/imsqti_v2p1"}


def _build_packer(name: str):
	return qti_package_maker.package_interface.QTIPackageInterface(
		name,
		verbose=False,
		allow_mixed=True,
	)


def _item_xmls(zip_path: str) -> list:
	# Return the bytes of every assessmentItem*.xml inside the package.
	with zipfile.ZipFile(zip_path, "r") as zf:
		names = sorted(n for n in zf.namelist() if n.startswith("qti21/assessmentItem"))
		return [zf.read(n) for n in names]


#============================================
def test_ultra_engine_all_item_types_round_trip(tmp_cwd):
	# Build every supported item type plus an ORDER (which must be dropped),
	# then verify the ZIP is valid and every emitted item re-parses as XML.
	qti_packer = _build_packer("ultra-roundtrip")
	qti_packer.add_item("MC", ("Pick one?", ["3", "4", "5"], "4"))
	qti_packer.add_item("MA", ("Pick all correct:", ["A", "B", "C"], ["A", "B"]))
	qti_packer.add_item("FIB", ("The sky is __.", ["blue"]))
	qti_packer.add_item("NUM", ("What is pi?", 3.14, 0.01))
	qti_packer.add_item("MULTI_FIB", ("Fill [a] and [b].", {"a": ["x"], "b": ["y"]}))
	qti_packer.add_item("MATCH", ("Match:", ["dog", "cat"], ["animal", "pet"]))
	qti_packer.add_item("ORDER", ("Arrange these.", ["first", "second", "third"]))

	outfile = qti_packer.save_package("bb_ultra_qti_v2_1")

	assert os.path.exists(outfile)
	assert zipfile.ZipFile(outfile).testzip() is None
	# Every item file must round-trip through lxml (parse without error).
	item_blobs = _item_xmls(outfile)
	assert item_blobs, "Ultra package produced no assessmentItem files"
	for blob in item_blobs:
		lxml.etree.fromstring(blob)


#============================================
def test_ultra_order_is_dropped(tmp_cwd):
	# Ultra does not support ORDER, so it must be dropped and the remaining
	# items must survive. Two MC inputs + one ORDER should yield two items.
	qti_packer = _build_packer("ultra-order-drop")
	qti_packer.add_item("MC", ("Q1?", ["X", "Y"], "X"))
	qti_packer.add_item("MC", ("Q2?", ["P", "Q"], "Q"))
	qti_packer.add_item("ORDER", ("Skip me.", ["a", "b", "c"]))

	outfile = qti_packer.save_package("bb_ultra_qti_v2_1")
	item_blobs = _item_xmls(outfile)
	# Exactly the two MC items remain.
	assert len(item_blobs) == 2


#============================================
def test_ultra_correct_response_references_real_choice(tmp_cwd):
	# Behavioral invariant: every correctResponse/value must be the identifier
	# of a real <simpleChoice> in the same item. Catches writer bugs where the
	# answer is serialized with the wrong naming scheme.
	qti_packer = _build_packer("ultra-response")
	qti_packer.add_item("MC", ("Pick correct:", ["Wrong1", "Correct", "Wrong2"], "Correct"))

	outfile = qti_packer.save_package("bb_ultra_qti_v2_1")
	for blob in _item_xmls(outfile):
		tree = lxml.etree.fromstring(blob)
		choice_ids = {c.get("identifier") for c in tree.findall(".//qti:simpleChoice", NS)}
		for value_elem in tree.findall(".//qti:correctResponse/qti:value", NS):
			assert value_elem.text in choice_ids


#============================================
def test_ultra_item_body_has_no_style_attributes(tmp_cwd):
	# The HTML sanitizer must strip style= everywhere inside itemBody.
	qti_packer = _build_packer("ultra-style")
	qti_packer.add_item("MC", ("Question?", ["Alpha", "Beta"], "Alpha"))

	outfile = qti_packer.save_package("bb_ultra_qti_v2_1")
	for blob in _item_xmls(outfile):
		tree = lxml.etree.fromstring(blob)
		for body in tree.findall(".//qti:itemBody", NS):
			for elem in body.iter():
				assert "style" not in elem.attrib
