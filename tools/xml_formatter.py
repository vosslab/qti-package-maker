#!/usr/bin/env python3

import os
import argparse

#PyPi
import lxml.etree

def format_xml_with_lxml(input_file: str) -> str:
	"""
	Parse an XML file and return a formatted XML string.
	"""
	# Parse the XML file, removing blank text to ensure proper formatting
	parser = lxml.etree.XMLParser(remove_blank_text=True)
	tree = lxml.etree.parse(input_file, parser)

	# Convert the XML tree to a pretty-printed string
	xml_string = lxml.etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="utf-8").decode("utf-8")
	return xml_string

#==============

def save_formatted_xml(formatted_xml: str, output_file: str) -> None:
	"""
	Saves the formatted XML to the specified output file.

	Args:
		formatted_xml (str): The formatted XML content.
		output_file (str): Path to save the formatted XML file.

	Returns:
		None
	"""
	with open(output_file, "w") as file:
		file.write(formatted_xml)
	print(f"Formatted XML written to {output_file}")

#==============

def parse_args() -> argparse.Namespace:
	"""
	Parses command-line arguments.

	Returns:
		argparse.Namespace: Parsed command-line arguments.
	"""
	parser = argparse.ArgumentParser(description="Format an XML file with BeautifulSoup prettify().")
	parser.add_argument("-i", "--input", required=True, help="Path to the input unformatted XML file.")
	return parser.parse_args()

#==============

def main() -> None:
	"""
	Main function to handle the script execution logic.
	"""
	args = parse_args()

	# Format the input XML file
	#formatted_xml = format_xml_with_bs(args.input)
	formatted_xml = format_xml_with_lxml(args.input)

	backup_file = args.input + ".bak"
	os.rename(args.input, backup_file)

	# Handle inplace editing
	save_formatted_xml(formatted_xml, args.input)

#==============

if __name__ == "__main__":
	main()
