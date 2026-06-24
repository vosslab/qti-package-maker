"""
Behavioral read test for the blackboard_export_zip read path (WP-R1).

Self-contained: builds its own minimal pool in tmp_path, so it depends on no
external sample data. The round-trip test covers parsing of every supported
type (including MATCH prompt->choice pairing recovery); this pins the one
reader behavior the round-trip cannot exercise: an unknown bbmd_questiontype is
skipped with a warning naming the type and source item, rather than crashing.
"""

# Standard Library
import pathlib

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines.blackboard_export_zip import read_package

#============================================
def test_unknown_question_type_is_skipped_with_warning(tmp_path, capsys) -> None:
	# An unknown bbmd_questiontype must be skipped with a warning naming the type
	# and source item, leaving the rest of the pool parseable.
	pool_dir = tmp_path / "pool"
	pool_dir.mkdir()
	_write_minimal_pool_with_unknown_type(pool_dir)
	bank = read_package.read_items_from_file(str(pool_dir), allow_mixed=True)
	# The unknown item is dropped; the bank parses without error.
	assert len(bank) == 0
	captured = capsys.readouterr()
	# The warning names the unknown type and identifies the source item.
	assert "Reticulating Splines" in captured.out
	assert "res00002.dat" in captured.out

#============================================
def _write_minimal_pool_with_unknown_type(pool_dir: pathlib.Path) -> None:
	"""
	Write a minimal pool directory whose single item has an unknown type.

	Args:
		pool_dir: A pathlib directory to populate with a manifest and pool dat.
	"""
	bb_ns = "http://www.blackboard.com/content-packaging/"
	# Minimal manifest declaring one assessment/x-bb-qti-pool resource.
	manifest = lxml.etree.Element(
		"manifest", nsmap={"bb": bb_ns}, attrib={"identifier": "man00001"}
	)
	resources = lxml.etree.SubElement(manifest, "resources")
	resource = lxml.etree.SubElement(resources, "resource")
	resource.set(f"{{{bb_ns}}}file", "res00002.dat")
	resource.set("identifier", "res00002")
	resource.set("type", "assessment/x-bb-qti-pool")
	manifest_bytes = lxml.etree.tostring(manifest, xml_declaration=True, encoding="UTF-8")
	(pool_dir / "imsmanifest.xml").write_bytes(manifest_bytes)

	# Minimal pool dat with one item carrying an unknown question type.
	questestinterop = lxml.etree.Element("questestinterop")
	assessment = lxml.etree.SubElement(questestinterop, "assessment")
	section = lxml.etree.SubElement(assessment, "section")
	item = lxml.etree.SubElement(section, "item")
	itemmetadata = lxml.etree.SubElement(item, "itemmetadata")
	qtype = lxml.etree.SubElement(itemmetadata, "bbmd_questiontype")
	qtype.text = "Reticulating Splines"
	pool_bytes = lxml.etree.tostring(questestinterop, xml_declaration=True, encoding="UTF-8")
	(pool_dir / "res00002.dat").write_bytes(pool_bytes)
