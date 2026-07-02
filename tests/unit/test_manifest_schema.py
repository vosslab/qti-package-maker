# Pip3 Library
import lxml.etree

# QTI Package Maker
from qti_package_maker.common import qti_manifest


def _text_at(root: lxml.etree._Element, xpath: str) -> str | None:
	node = root.find(xpath)
	return node.text if node is not None else None


def test_manifest_schema_location_present() -> None:
	tree = qti_manifest.generate_manifest("dummy", ["qti12_items/qti12_items.xml"], version="1.2")
	root = tree.getroot()
	schema_location = root.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation")
	assert schema_location
	assert "imscp_v1p1.xsd" in schema_location


def test_manifest_metadata_v1_2_schema() -> None:
	tree = qti_manifest.generate_manifest("dummy", ["qti12_items/qti12_items.xml"], version="1.2")
	root = tree.getroot()
	assert _text_at(root, ".//metadata/schema") == "IMS Content"
	assert _text_at(root, ".//metadata/schemaversion") == "1.1.3"


def test_manifest_metadata_v2_1_schema() -> None:
	tree = qti_manifest.generate_manifest("dummy", ["qti21_items/assessmentItem00001.xml"], version="2.1")
	root = tree.getroot()
	assert _text_at(root, ".//metadata/schema") == "QTIv2.1"
	assert _text_at(root, ".//metadata/schemaversion") == "2.0"
