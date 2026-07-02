#!/usr/bin/env python3

import os
import lxml.etree

#==============
def generate_assessment_meta(package_name: str, assessment_file_name_list: list) -> lxml.etree.ElementTree:
	"""
	Generates the XML for the question bank (assessment_meta.xml).

	Args:
		package_name (str): The title for the set of assessments.
		assessment_file_name_list (list[str]): List of assessment item file names.

	Returns:
		lxml.etree.ElementTree: The generated XML tree for assessment_meta.xml.
	"""
	if not assessment_file_name_list or len(assessment_file_name_list) == 0:
		raise ValueError("Cannot generate assessment meta: No assessment files provided.")

	assessment_meta = create_assessment_meta_header(package_name)
	assessment_section = create_assessment_section(assessment_file_name_list)
	assessment_meta.append(assessment_section)

	return lxml.etree.ElementTree(assessment_meta)

#==============
def create_assessment_meta_header(package_name: str) -> lxml.etree.Element:
	"""
	Creates the root element for the question bank XML, including namespaces and custom attribute order.

	Args:
		package_name (str): The title for the set of assessments.

	Returns:
		lxml.etree.Element: The root 'assessmentTest' element with attributes in the desired order.
	"""
	# Define namespaces
	nsmap = {
		None: "http://www.imsglobal.org/xsd/imsqti_v2p1",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance"
	}

	# Create the root element with namespaces
	assessment_test = lxml.etree.Element("assessmentTest", nsmap=nsmap)

	# Add the xsi:schemaLocation attribute first
	assessment_test.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
		"http://www.imsglobal.org/xsd/imsqti_v2p1 "
		"http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"
	)

	# Add identifier and title attributes next
	assessment_test.set("identifier", "assessment_meta")
	assessment_test.set("title", package_name)

	return assessment_test

#==============
def create_assessment_section(assessment_file_name_list: list) -> lxml.etree.Element:
	"""
	Creates the assessment section, which references all assessment items.

	Args:
		assessment_file_name_list (list): List of assessment item file names.

	Returns:
		lxml.etree.Element: The 'testPart' element containing assessment item references.
	"""
	if len(assessment_file_name_list) == 0:
		raise ValueError("assessment_file_name_list is empty")

	test_part = lxml.etree.Element("testPart", identifier="test_part",
		navigationMode="nonlinear", submissionMode="simultaneous")

	# Add an assessment section referencing each assessment item file
	assessment_ref = lxml.etree.Element("assessmentSection",
		identifier="section_part", visible="false", title="Question Pool")
	for assessment_file_name in assessment_file_name_list:
		assessment_base_name = os.path.basename(assessment_file_name)
		assessment_core_name = os.path.splitext(assessment_base_name)[0]
		item_ref = lxml.etree.SubElement(assessment_ref, "assessmentItemRef",
			identifier=assessment_core_name,
			href=assessment_base_name)
		assessment_ref.append(item_ref)
	test_part.append(assessment_ref)

	return test_part

#==============
#==============
def dummy_test_run() -> None:
	# Generate assessment_meta00001.xml
	assessment_file_name_list = [
		'item_00001.xml',
		'item_00002.xml',
		#'item_00003.xml',
	]
	package_name = "Questions about Blah Blah Blah"
	assessment_meta_etree = generate_assessment_meta(package_name, assessment_file_name_list)

	#write to file
	assessment_meta_xml_string = lxml.etree.tostring(assessment_meta_etree, pretty_print=True,
		xml_declaration=True, encoding="UTF-8")
	assessment_meta_path = "assessment_meta.xml"
	with open(assessment_meta_path, "w", encoding="utf-8") as f:
		f.write(assessment_meta_xml_string.decode("utf-8"))

#==============
#==============
if __name__ == "__main__":
	dummy_test_run()


