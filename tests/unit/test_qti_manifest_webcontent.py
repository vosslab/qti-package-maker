# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import qti_manifest
from qti_package_maker.common import media_assets


def _make_asset(src: str, output_name: str) -> media_assets.MediaAsset:
	# manifest emission only reads output_name (the href); no file I/O needed
	return media_assets.MediaAsset(src=src, kind=media_assets.KIND_LOCAL, output_name=output_name)


def test_webcontent_resource_emitted_per_asset() -> None:
	asset = _make_asset("images/figure.png", "figure.png")
	files = ["qti21_items/item_00001.xml"]
	resources = qti_manifest.create_resources_section(
		files, version="2.1", assets=[asset], item_dependencies={files[0]: [asset]})

	webcontent_resources = resources.findall("resource[@type='webcontent']")
	assert len(webcontent_resources) == 1
	assert webcontent_resources[0].get("href") == "figure.png"
	assert webcontent_resources[0].find("file").get("href") == "figure.png"


def test_item_resource_gets_dependency_on_its_asset() -> None:
	asset = _make_asset("images/figure.png", "figure.png")
	files = ["qti21_items/item_00001.xml"]
	resources = qti_manifest.create_resources_section(
		files, version="2.1", assets=[asset], item_dependencies={files[0]: [asset]})

	item_resource = resources.find("resource[@identifier='item_00001']")
	webcontent_identifier = resources.find("resource[@type='webcontent']").get("identifier")
	dependency_refs = [dep.get("identifierref") for dep in item_resource.findall("dependency")]
	assert webcontent_identifier in dependency_refs
	# the item resource still keeps its assessment_meta dependency
	assert "assessment_meta" in dependency_refs


def test_shared_asset_produces_one_resource_with_multiple_dependencies() -> None:
	# two items referencing the SAME MediaAsset object (identity is the src,
	# matching how ItemBank.collect_assets() reuses one record per src)
	shared_asset = _make_asset("images/shared.jpg", "shared.jpg")
	files = ["qti21_items/item_00001.xml", "qti21_items/item_00002.xml"]
	dependencies = {files[0]: [shared_asset], files[1]: [shared_asset]}
	resources = qti_manifest.create_resources_section(
		files, version="2.1", assets=[shared_asset], item_dependencies=dependencies)

	webcontent_resources = resources.findall("resource[@type='webcontent']")
	assert len(webcontent_resources) == 1
	shared_identifier = webcontent_resources[0].get("identifier")

	for file_name in files:
		base_name = file_name.split("/")[-1].split(".")[0]
		item_resource = resources.find(f"resource[@identifier='{base_name}']")
		dependency_refs = [dep.get("identifierref") for dep in item_resource.findall("dependency")]
		assert shared_identifier in dependency_refs


def test_item_with_no_referenced_assets_gets_no_webcontent_dependency() -> None:
	asset = _make_asset("images/figure.png", "figure.png")
	files = ["qti21_items/item_00001.xml", "qti21_items/item_00002.xml"]
	# only the first item references the asset; the second has none
	resources = qti_manifest.create_resources_section(
		files, version="2.1", assets=[asset], item_dependencies={files[0]: [asset]})

	second_item_resource = resources.find("resource[@identifier='item_00002']")
	dependency_refs = [dep.get("identifierref") for dep in second_item_resource.findall("dependency")]
	assert dependency_refs == ["assessment_meta"]


def test_old_signature_without_assets_emits_no_webcontent_resources() -> None:
	files = ["qti21_items/item_00001.xml"]
	resources = qti_manifest.create_resources_section(files, version="2.1")

	assert resources.findall("resource[@type='webcontent']") == []
	item_resource = resources.find("resource[@identifier='item_00001']")
	dependency_refs = [dep.get("identifierref") for dep in item_resource.findall("dependency")]
	assert dependency_refs == ["assessment_meta"]


def test_generate_manifest_old_call_shape_still_works() -> None:
	# generate_manifest is called positionally by every existing writer engine;
	# confirm the two new keyword-only params do not break that call shape
	tree = qti_manifest.generate_manifest("dummy", ["qti21_items/item_00001.xml"], version="2.1")
	root = tree.getroot()
	assert root.findall(".//resources/resource[@type='webcontent']") == []


def test_generate_manifest_with_assets_declares_webcontent_and_dependency() -> None:
	asset = _make_asset("images/figure.png", "figure.png")
	files = ["qti21_items/item_00001.xml"]
	tree = qti_manifest.generate_manifest(
		"dummy", files, version="2.1", assets=[asset], item_dependencies={files[0]: [asset]})
	root = tree.getroot()

	webcontent_resources = root.findall(".//resources/resource[@type='webcontent']")
	assert len(webcontent_resources) == 1
	item_resource = root.find(".//resources/resource[@identifier='item_00001']")
	dependency_refs = [dep.get("identifierref") for dep in item_resource.findall("dependency")]
	assert webcontent_resources[0].get("identifier") in dependency_refs
