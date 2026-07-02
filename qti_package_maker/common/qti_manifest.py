#!/usr/bin/env python3

# Standard Library
import os
import datetime

# Pip3 Library
import lxml.etree

# QTI Package Maker
from qti_package_maker.common import media_assets

#========================================================
def generate_manifest(
			package_name: str,
			assessment_file_name_list: list[str],
			version: str = "1.2",
			assets: list[media_assets.MediaAsset] | None = None,
			item_dependencies: dict[str, list[media_assets.MediaAsset]] | None = None,
			) -> lxml.etree.ElementTree:
	"""
	Generates the imsmanifest.xml file as an lxml.etree ElementTree.

	Args:
		package_name: Display name of the package, written into the metadata title.
		assessment_file_name_list (list[str]): List of assessment item file names.
		version: QTI version string, e.g. "1.2" or "2.1".
		assets: Optional list of resolved MediaAsset records to declare as
			webcontent resources. None preserves the pre-image-support
			manifest shape.
		item_dependencies: Optional map of assessment file name (a member of
			assessment_file_name_list) to the MediaAsset records that item
			references, so each referencing item resource gets a `<dependency>`
			pointing at the shared webcontent resource.

	Returns:
		lxml.etree.ElementTree: The generated XML tree for imsmanifest.xml.
	"""
	if not assessment_file_name_list:
		raise ValueError("Cannot generate manifest: No assessment files provided.")
	if version.startswith("1"):
		if len(assessment_file_name_list) > 1:
			raise ValueError("QTI version 1, only supports one assessment_file")
		file_name = assessment_file_name_list[0]
		base_name = os.path.splitext(os.path.basename(file_name))[0]
		dir_name = os.path.dirname(file_name)
		if base_name != dir_name:
			raise ValueError("QTI version 1, requires file_name to match dir_name")

	manifest = create_manifest_header()
	metadata = create_metadata_section(package_name, version)
	# Empty <organizations/> element; real Blackboard Learn exports carry this
	# element (even when empty) before <resources>, matching
	# SAMPLES/blackboard_learn_classic-qti21_export/imsmanifest.xml.
	organizations = lxml.etree.Element("organizations")
	sorted_file_list = sorted(assessment_file_name_list)
	resources = create_resources_section(
		sorted_file_list, version, assets=assets, item_dependencies=item_dependencies)

	# Add sections to the manifest
	manifest.append(metadata)
	manifest.append(organizations)
	manifest.append(resources)

	return lxml.etree.ElementTree(manifest)

#========================================================
def create_manifest_header() -> lxml.etree.Element:
	"""
	Creates the header element for the manifest, including namespaces and identifiers.

	Returns:
		lxml.etree.Element: The root 'manifest' element with attributes.
	"""
	# Define namespaces
	nsmap = {
		None: "http://www.imsglobal.org/xsd/imscp_v1p1",  # Default namespace
		"lom": "http://ltsc.ieee.org/xsd/LOM",
		"imsmd": "http://www.imsglobal.org/xsd/imsmd_v1p2",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance",
	}

	# Create the root element with namespaces and identifier attribute. Must be
	# a legal xs:ID token (no spaces); "main_manifest" is a clear, readable
	# label rather than mirroring Blackboard's cryptic "man00001" convention.
	manifest = lxml.etree.Element("manifest", nsmap=nsmap, identifier="main_manifest")

	# Define the xsi:schemaLocation attribute with correct values
	manifest.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
		"http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p1.xsd "
		"http://www.imsglobal.org/xsd/imsmd_v1p2 http://www.imsglobal.org/xsd/imsmd_v1p2.xsd "
		"http://ltsc.ieee.org/xsd/LOM http://ieee-sa.imeetcentral.com/ltsc/"
	)

	return manifest

#========================================================
def create_metadata_section(package_name: str, version: str = "1.2") -> lxml.etree.Element:
	"""
	Creates the metadata section of the manifest.

	Args:
		package_name (str): The name of the package.
		version (str): The version of QTI (default is "1.2").

	Returns:
		lxml.etree.Element: The 'metadata' element with its child elements.
	"""
	# Define the IMSMD namespace
	ns_imsmd = "http://www.imsglobal.org/xsd/imsmd_v1p2"

	# Create the root metadata element
	metadata = lxml.etree.Element("metadata")

	# Add schema and schemaversion
	schema = lxml.etree.SubElement(metadata, "schema")

	schema_version = lxml.etree.SubElement(metadata, "schemaversion")
	if version.startswith("2"):
		schema_version.text = "2.0"
		schema.text = f"QTIv{version}"
	else:
		schema_version.text ="1.1.3"
		#schema.text = f"QTIv{version}"
		schema.text = "IMS Content"

	# Create the <imsmd:lom> structure
	lom = lxml.etree.SubElement(metadata, f"{{{ns_imsmd}}}lom", nsmap={"imsmd": ns_imsmd})

	# <imsmd:general> section
	general = lxml.etree.SubElement(lom, f"{{{ns_imsmd}}}general")
	title = lxml.etree.SubElement(general, f"{{{ns_imsmd}}}title")
	title_string = lxml.etree.SubElement(title, f"{{{ns_imsmd}}}string")
	title_string.text = package_name

	# <imsmd:lifeCycle> section
	life_cycle = lxml.etree.SubElement(lom, f"{{{ns_imsmd}}}lifeCycle")
	contribute = lxml.etree.SubElement(life_cycle, f"{{{ns_imsmd}}}contribute")

	# Get the current date in ISO format (YYYY-MM-DD)
	current_date = datetime.date.today().isoformat()
	date = lxml.etree.SubElement(contribute, f"{{{ns_imsmd}}}date")
	date_time = lxml.etree.SubElement(date, f"{{{ns_imsmd}}}dateTime")
	date_time.text = current_date

	# <imsmd:rights> section
	rights = lxml.etree.SubElement(lom, f"{{{ns_imsmd}}}rights")

	# CC BY 4.0 License
	description = lxml.etree.SubElement(rights, f"{{{ns_imsmd}}}description")
	license_string = lxml.etree.SubElement(description, f"{{{ns_imsmd}}}string")
	license_string.text = "CC Attribution - http://creativecommons.org/licenses/by/4.0"

	return metadata

#========================================================
def _build_webcontent_resources(
			assets: list[media_assets.MediaAsset]) -> tuple[list[lxml.etree.Element], dict[int, str]]:
	"""
	Build one <resource type="webcontent"> + <file href> per asset.

	Identifiers are minted in list order as `ccresNNNNN` (5-digit, 1-based),
	matching `SAMPLES/blackboard_learn_classic-qti21_export` and
	`ULTRA/image_test`. The href is the asset's collision-safe output_name,
	written at the package root, matching those same samples.

	Args:
		assets: Resolved MediaAsset records to declare (identity is the src;
			the caller is responsible for passing each shared asset once).

	Returns:
		Tuple of (webcontent resource elements in list order, a map from
		`id(asset)` to its minted identifier so item resources can reference
		it via `<dependency identifierref>`).
	"""
	webcontent_elements = []
	identifier_by_asset_id = {}
	for asset_index, asset in enumerate(assets, start=1):
		identifier = f"ccres{asset_index:05d}"
		# the same asset object is reused across items that share a src, so
		# identity (id()) is the correct key -- MediaAsset is not hashable
		identifier_by_asset_id[id(asset)] = identifier
		webcontent_resource = lxml.etree.Element(
			"resource",
			href=asset.output_name,
			identifier=identifier,
			type="webcontent",
		)
		lxml.etree.SubElement(webcontent_resource, "file", href=asset.output_name)
		webcontent_elements.append(webcontent_resource)
	return webcontent_elements, identifier_by_asset_id

#========================================================
def create_resources_section(
			assessment_file_name_list: list[str],
			version: str = "1.2",
			assets: list[media_assets.MediaAsset] | None = None,
			item_dependencies: dict[str, list[media_assets.MediaAsset]] | None = None,
			) -> lxml.etree.Element:
	"""
	Creates the resources section of the manifest, adding each assessment item.

	Args:
		assessment_file_name_list (list[str]): List of assessment item file names.
		version (str): The version of QTI (default is "1.2").
		assets: Optional list of resolved MediaAsset records. Each
			distinct asset emits exactly one `<resource type="webcontent">` +
			`<file href>`, placed before the item resources. None (the default)
			preserves the pre-image-support manifest shape exactly, so existing
			callers keep working unchanged.
		item_dependencies: Optional map of assessment file name (a member of
			assessment_file_name_list) to the MediaAsset records that item
			references. A shared asset referenced by multiple items produces
			one webcontent resource with one `<dependency>` on each referencing
			item resource (pattern matches `SAMPLES` QTI 2.1 + `ULTRA/image_test`).

	Returns:
		lxml.etree.Element: The 'resources' element containing resource elements.
	"""
	resources = lxml.etree.Element("resources")

	if version.startswith("2"):
		meta_type = "imsqti_test_xmlv2p1"
		item_type = "imsqti_item_xmlv2p1"
	else:
		item_type = "imsqti_xmlv1p2"
		#item_type = "imsqti_item_xmlv1p2"
		meta_type = "associatedcontent/imscc_xmlv1p1/learning-application-resource"
		#meta_type = "imsqti_xmlv1p2"

	dir_name = os.path.dirname(assessment_file_name_list[0])
	meta_file_path = f"{dir_name}/assessment_meta.xml"

	# Create the assessment meta resource (we will add dependencies later)
	assessment_meta_resource = lxml.etree.Element(
		"resource",
		href=meta_file_path,
		identifier="assessment_meta",
		type=meta_type,
	)
	lxml.etree.SubElement(assessment_meta_resource, "file", href=meta_file_path)

	# Webcontent resources are declared before the item resources, matching
	# SAMPLES/blackboard_learn_classic-qti21_export and ULTRA/image_test.
	identifier_by_asset_id: dict[int, str] = {}
	if assets:
		webcontent_elements, identifier_by_asset_id = _build_webcontent_resources(assets)
		for webcontent_element in webcontent_elements:
			resources.append(webcontent_element)
	# item_dependencies is genuinely optional (an item may reference no assets)
	if item_dependencies is None:
		item_dependencies = {}

	# Create individual assessment item resources
	for file_name in assessment_file_name_list:
		base_name = os.path.splitext(os.path.basename(file_name))[0]
		resource = lxml.etree.Element(
			"resource",
			href=file_name,
			identifier=base_name,
			type=item_type,
		)
		lxml.etree.SubElement(resource, "file", href=file_name)

		# Add dependency to assessment_meta
		lxml.etree.SubElement(resource, "dependency", identifierref="assessment_meta")

		# Also add reverse dependency in assessment_meta
		lxml.etree.SubElement(assessment_meta_resource, "dependency", identifierref=base_name)

		# Add one <dependency> per asset this item references (each asset's
		# identifier was already minted, so a shared asset naturally produces
		# one dependency per referencing item against the same identifier).
		for asset in item_dependencies.get(file_name, []):
			lxml.etree.SubElement(
				resource, "dependency", identifierref=identifier_by_asset_id[id(asset)])

		resources.append(resource)

	# Append assessment_meta after all assessment items
	resources.append(assessment_meta_resource)

	return resources

#========================================================
def dummy_test_run() -> None:
	# Generate imsmanifest.xml
	assessment_file_name_list = [
		'qti21_items/assessmentItem00001.xml',
		'qti21_items/assessmentItem00002.xml',
		#'qti21_items/assessmentItem00003.xml',
	]
	manifest_etree = generate_manifest("dummy set", assessment_file_name_list, version="2.1")
	manifest_xml_string = lxml.etree.tostring(manifest_etree, pretty_print=True,
		xml_declaration=True, encoding="UTF-8")
	manifest_path = "imsmanifest_v2_1.xml"
	with open(manifest_path, "w", encoding="utf-8") as f:
		f.write(manifest_xml_string.decode("utf-8"))

	# Generate imsmanifest.xml
	assessment_file_name_list = [
		'qti12_items/qti12_items.xml',
	]
	manifest_etree = generate_manifest("dummy set", assessment_file_name_list, version="1.2")
	manifest_xml_string = lxml.etree.tostring(manifest_etree, pretty_print=True,
		xml_declaration=True, encoding="UTF-8")
	manifest_path = "imsmanifest_v1_2.xml"
	with open(manifest_path, "w", encoding="utf-8") as f:
		f.write(manifest_xml_string.decode("utf-8"))

#========================================================
if __name__ == "__main__":
	dummy_test_run()
