# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.common import qti_manifest


def test_manifest_qti12_rejects_multiple_files() -> None:
	with pytest.raises(ValueError):
		qti_manifest.generate_manifest("dummy", ["a/a.xml", "b/b.xml"], version="1.2")


def test_manifest_qti12_rejects_mismatched_dir_and_base() -> None:
	with pytest.raises(ValueError):
		qti_manifest.generate_manifest("dummy", ["qti12_items/assessment.xml"], version="1.2")


def test_manifest_rejects_empty_file_list() -> None:
	with pytest.raises(ValueError):
		qti_manifest.generate_manifest("dummy", [], version="2.1")


def test_manifest_qti12_resources_include_meta() -> None:
	tree = qti_manifest.generate_manifest("dummy", ["qti12_items/qti12_items.xml"], version="1.2")
	root = tree.getroot()
	resources = root.findall(".//resources/resource")
	assert len(resources) >= 2

	resource_ids = {resource.get("identifier") for resource in resources}
	assert "assessment_meta" in resource_ids


def test_manifest_qti21_dependencies() -> None:
	files = ["qti21_items/item_00001.xml", "qti21_items/item_00002.xml"]
	tree = qti_manifest.generate_manifest("dummy", files, version="2.1")
	root = tree.getroot()
	resources = root.findall(".//resources/resource")
	resource_map = {resource.get("identifier"): resource for resource in resources}
	assert "assessment_meta" in resource_map

	for file_name in files:
		item_id = file_name.split("/")[-1].split(".")[0]
		item_resource = resource_map[item_id]
		deps = [dep.get("identifierref") for dep in item_resource.findall("dependency")]
		assert "assessment_meta" in deps

	meta_resource = resource_map["assessment_meta"]
	meta_deps = {dep.get("identifierref") for dep in meta_resource.findall("dependency")}
	assert meta_deps == {"item_00001", "item_00002"}
