"""Ultra-specific manifest and question_bank builders."""

import lxml.etree


#============================================
def get_item_identifier(item_number: int) -> str:
	"""
	Generate a 5-digit zero-padded assessment item identifier.

	Args:
		item_number: 1-indexed item number.

	Returns:
		str: Identifier like "assessmentItem00001".
	"""
	return f"assessmentItem{item_number:05d}"


#============================================
def get_item_filename(item_number: int) -> str:
	"""
	Generate a 5-digit zero-padded assessment item filename.

	Args:
		item_number: 1-indexed item number.

	Returns:
		str: Filename like "assessmentItem00001.xml".
	"""
	return f"assessmentItem{item_number:05d}.xml"


#============================================
def generate_manifest(item_count: int) -> lxml.etree.ElementTree:
	"""
	Generate the Ultra manifest (imsmanifest.xml).

	Args:
		item_count: Number of assessment items in the package.

	Returns:
		lxml.etree.ElementTree: The manifest tree.
	"""
	# Define namespaces for Ultra manifest
	nsmap = {
		None: "http://www.imsglobal.org/xsd/imscp_v1p1",
		"csm": "http://www.imsglobal.org/xsd/imsccv1p2/imscsmd_v1p0",
		"imsmd": "http://ltsc.ieee.org/xsd/LOM",
		"imsqti": "http://www.imsglobal.org/xsd/imsqti_metadata_v2p1",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance",
	}

	# Root manifest element
	manifest = lxml.etree.Element(
		"manifest",
		nsmap=nsmap,
		attrib={
			"identifier": "man00001",
			"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
				"http://www.imsglobal.org/xsd/imscp_v1p1 "
				"http://www.imsglobal.org/xsd/imscp_v1p2.xsd "
				"http://ltsc.ieee.org/xsd/LOM imsmd_loose_v1p3.xsd "
				"http://www.imsglobal.org/xsd/imsqti_metadata_v2p1 "
				"http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_metadata_v2p1.xsd "
				"http://www.imsglobal.org/xsd/imsccv1p2/imscsmd_v1p0 "
				"http://www.imsglobal.org/profile/cc/ccv1p2/ccv1p2_imscsmd_v1p0.xsd"
			),
		},
	)

	# Metadata section
	metadata = lxml.etree.SubElement(manifest, "metadata")
	lxml.etree.SubElement(metadata, "schema").text = "QTIv2.1"
	lxml.etree.SubElement(metadata, "schemaversion").text = "2.0"

	# Organizations (empty for Ultra)
	lxml.etree.SubElement(manifest, "organizations")

	# Resources section
	resources = lxml.etree.SubElement(manifest, "resources")

	# Test resource (question_bank00001.xml) with dependencies on all items
	test_resource = lxml.etree.SubElement(resources, "resource", {
		"href": "qti21/question_bank00001.xml",
		"identifier": "question_bank00001",
		"type": "imsqti_test_xmlv2p1",
	})
	lxml.etree.SubElement(test_resource, "file", {
		"href": "qti21/question_bank00001.xml",
	})

	# Add dependencies on all assessment items
	for item_num in range(1, item_count + 1):
		item_id = get_item_identifier(item_num)
		lxml.etree.SubElement(test_resource, "dependency", {
			"identifierref": item_id,
		})

	# Assessment item resources (one per item)
	for item_num in range(1, item_count + 1):
		item_id = get_item_identifier(item_num)
		item_filename = get_item_filename(item_num)
		item_resource = lxml.etree.SubElement(resources, "resource", {
			"href": f"qti21/{item_filename}",
			"identifier": item_id,
			"type": "imsqti_item_xmlv2p1",
		})
		lxml.etree.SubElement(item_resource, "file", {
			"href": f"qti21/{item_filename}",
		})

	return lxml.etree.ElementTree(manifest)


#============================================
def _humanize_package_name(package_name: str) -> str:
	"""
	Turn a snake_case package name into a human-readable title.

	Underscores become spaces; hyphens are preserved (they often carry
	meaning, like a trailing subject tag in `michaelis_menten_table-Km`).
	"""
	return package_name.replace("_", " ")


#============================================
def generate_question_bank(item_count: int, package_name: str) -> lxml.etree.ElementTree:
	"""
	Generate the Ultra question_bank00001.xml test file.

	Args:
		item_count: Number of assessment items in the package.
		package_name: Name of the package, used as the assessment test title.

	Returns:
		lxml.etree.ElementTree: The question_bank tree.
	"""
	# Define namespaces for Ultra test file
	nsmap = {
		None: "http://www.imsglobal.org/xsd/imsqti_v2p1",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance",
	}

	# Root assessmentTest element
	test_title = _humanize_package_name(package_name)
	assessment_test = lxml.etree.Element(
		"assessmentTest",
		nsmap=nsmap,
		attrib={
			"identifier": "question_bank00001",
			"title": test_title,
			"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
				"http://www.imsglobal.org/xsd/imsqti_v2p1 "
				"http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"
			),
		},
	)

	# Test part
	test_part = lxml.etree.SubElement(assessment_test, "testPart", {
		"identifier": "question_bank00001_1",
		"navigationMode": "nonlinear",
		"submissionMode": "simultaneous",
	})

	# Assessment section
	assessment_section = lxml.etree.SubElement(test_part, "assessmentSection", {
		"identifier": "question_bank00001_1_1",
		"visible": "false",
		"title": "Section 1",
	})

	# Add assessment item references
	for item_num in range(1, item_count + 1):
		item_id = get_item_identifier(item_num)
		item_filename = get_item_filename(item_num)
		lxml.etree.SubElement(assessment_section, "assessmentItemRef", {
			"identifier": item_id,
			"href": item_filename,
		})

	return lxml.etree.ElementTree(assessment_test)
