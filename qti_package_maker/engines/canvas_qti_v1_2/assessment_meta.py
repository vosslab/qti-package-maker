#!/usr/bin/env python3

#import os
import lxml.etree

#==============
def generate_assessment_meta(package_name: str) -> lxml.etree.ElementTree:
	"""
	Generates the XML for the question bank (assessment_meta.xml).

	Args:
		package_name (str): The title for the set of assessments.

	Returns:
		lxml.etree.ElementTree: The generated XML tree for assessment_meta.xml.
	"""
	# Define namespaces
	nsmap = {
		None: "http://canvas.instructure.com/xsd/cccv1p0",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance"
	}

	# Create the root element <quiz> with namespaces
	quiz = lxml.etree.Element("quiz", nsmap=nsmap)

	# Add the xsi:schemaLocation attribute
	quiz.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"] = (
		"http://canvas.instructure.com/xsd/cccv1p0 "
		"https://canvas.instructure.com/xsd/cccv1p0.xsd"
	)

	# Add identifier attribute
	quiz.set("identifier", "assessment_meta")

	# Add <title>
	title_element = lxml.etree.SubElement(quiz, "title")
	title_element.text = package_name

	# Add <assignment>
	assignment_element = lxml.etree.SubElement(quiz, "assignment", identifier="assignment_name")

	# Add <title> inside <assignment>
	assignment_title = lxml.etree.SubElement(assignment_element, "title")
	assignment_title.text = package_name

	return lxml.etree.ElementTree(quiz)

#==============
def dummy_test_run() -> None:
	"""
	Run a test generation of assessment_meta.xml with a sample package name.
	"""
	package_name = "Questions about Blah Blah Blah"
	assessment_meta_etree = generate_assessment_meta(package_name)

	# Write to file
	assessment_meta_xml_string = lxml.etree.tostring(
		assessment_meta_etree, pretty_print=True, xml_declaration=True, encoding="UTF-8"
	)
	assessment_meta_path = "assessment_meta.xml"
	with open(assessment_meta_path, "w", encoding="utf-8") as f:
		f.write(assessment_meta_xml_string.decode("utf-8"))

#==============
if __name__ == "__main__":
	dummy_test_run()
