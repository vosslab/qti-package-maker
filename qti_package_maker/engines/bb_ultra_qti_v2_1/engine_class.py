"""Blackboard Ultra QTI 2.1 engine implementation."""

# Standard Library
import os
import re
import time
import shutil
import zipfile

# Pip3 Library
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.bb_ultra_qti_v2_1 import write_item
from qti_package_maker.engines.bb_ultra_qti_v2_1 import assessment_meta
from qti_package_maker.engines.bb_ultra_qti_v2_1 import type_normalize
from qti_package_maker.engines.bb_ultra_qti_v2_1 import compat_gate


#============================================
def _add_readability_spacing(xml_text: str) -> str:
	"""
	Add blank lines between major QTI 2.1 XML blocks for easier manual inspection.
	"""
	xml_text = re.sub(r"(</responseDeclaration>\n)(\s*<outcomeDeclaration\b)", r"\1\n\2", xml_text)
	xml_text = re.sub(r"(<outcomeDeclaration\b[^>]*\/>\n)(\s*<itemBody>)", r"\1\n\2", xml_text)
	xml_text = re.sub(r"(</outcomeDeclaration>\n)(\s*<itemBody>)", r"\1\n\2", xml_text)
	xml_text = re.sub(r"(</itemBody>\n)(\s*<responseProcessing\b)", r"\1\n\2", xml_text)
	if not xml_text.endswith("\n"):
		xml_text += "\n"
	return xml_text


#============================================
class EngineClass(base_engine.BaseEngine):
	"""
	Blackboard Ultra QTI 2.1 engine that packages items into a ZIP bundle.
	"""
	def __init__(self, package_name: str, verbose: bool = False):
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# Set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()
		# Setup directories
		self._setup_directories()

	#============================================
	def _setup_directories(self):
		"""
		Initialize output paths for the Ultra QTI 2.1 bundle.
		"""
		current_time = time.strftime("%H%M")
		self.output_dir = os.path.join(
			os.getcwd(),
			f"QTI21-Ultra-{self.package_name}_package_{current_time}"
		)
		self.qti21_dir = os.path.join(self.output_dir, "qti21")
		self.csfiles_dir = os.path.join(self.output_dir, "csfiles")
		self.csfiles_home_dir = os.path.join(self.csfiles_dir, "home_dir")

	#============================================
	def read_package(self, infile: str):
		"""
		Read is not supported for this engine.
		"""
		raise NotImplementedError

	#============================================
	def write_assessment_items(self, item_bank):
		"""
		Write each assessment item into its own Ultra QTI 2.1 XML file.

		Normalizes item types first (drops ORDER items with warnings).

		Returns:
			tuple: (count, etrees) where count is the number of items written
				and etrees is a list of the assessment item etrees.
		"""
		if len(item_bank) == 0:
			print("No items to write, skipping")
			return 0, []

		# Normalize items: drop ORDER, keep supported types
		normalized_items, warnings = type_normalize.normalize_items(
			list(item_bank),
			ultra_order_mapping="skip"
		)

		# Log warnings if any
		if self.verbose and warnings:
			for warning in warnings:
				print(f"Warning: {warning}")

		# Process normalized items through the engine
		assessment_items_tree = self.process_item_bank(normalized_items)

		# Write each item to its own file
		self.save_count = 0
		for item_number, assessment_item_etree in enumerate(assessment_items_tree, start=1):
			item_filename = f"assessmentItem{item_number:05d}.xml"
			item_filepath = os.path.join(self.qti21_dir, item_filename)

			if assessment_item_etree is None:
				print(f"No data to write for item {item_number}, skipping")
				continue

			# Convert to XML string
			assessment_item_xml_string = lxml.etree.tostring(
				assessment_item_etree,
				pretty_print=True,
				xml_declaration=True,
				encoding="UTF-8"
			)

			# Write to file
			with open(item_filepath, "w", encoding="utf-8") as f:
				xml_text = assessment_item_xml_string.decode("utf-8")
				xml_text = _add_readability_spacing(xml_text)
				f.write(xml_text)
				self.save_count += 1

		if self.verbose:
			print(f"Wrote {self.save_count} assessment items for {self.package_name}")

		return self.save_count, assessment_items_tree

	#============================================
	def write_assessment_meta(self, item_count: int):
		"""
		Write the question_bank00001.xml test file.

		Args:
			item_count: Number of items in the package.
		"""
		question_bank_etree = assessment_meta.generate_question_bank(item_count, self.package_name)
		question_bank_xml_string = lxml.etree.tostring(
			question_bank_etree,
			pretty_print=True,
			xml_declaration=True,
			encoding="UTF-8"
		)
		question_bank_path = os.path.join(self.qti21_dir, "question_bank00001.xml")
		with open(question_bank_path, "w", encoding="utf-8") as f:
			xml_text = question_bank_xml_string.decode("utf-8")
			xml_text = _add_readability_spacing(xml_text)
			f.write(xml_text)

	#============================================
	def write_manifest(self, item_count: int):
		"""
		Write the imsmanifest.xml file.

		Args:
			item_count: Number of items in the package.
		"""
		manifest_etree = assessment_meta.generate_manifest(item_count)
		manifest_xml_string = lxml.etree.tostring(
			manifest_etree,
			pretty_print=True,
			xml_declaration=True,
			encoding="UTF-8"
		)
		manifest_path = os.path.join(self.output_dir, "imsmanifest.xml")
		with open(manifest_path, "w", encoding="utf-8") as f:
			xml_text = manifest_xml_string.decode("utf-8")
			xml_text = _add_readability_spacing(xml_text)
			f.write(xml_text)

	#============================================
	def save_package(self, item_bank, outfile: str = None):
		"""
		Write assessment XML, metadata, and manifest, then bundle the ZIP.

		Runs the compatibility gate on all assessment items before writing
		the ZIP file. Hard-fail violations raise UltraCompatibilityError.

		Args:
			item_bank: Iterable of assessment items.
			outfile: Optional output filename. If not provided, generates one.

		Returns:
			str: Path to the created ZIP file.
		"""
		# Create necessary directories
		os.makedirs(self.qti21_dir, exist_ok=True)
		os.makedirs(self.csfiles_home_dir, exist_ok=True)

		# Write assessment items and get the etrees for validation
		item_count, assessment_items_tree = self.write_assessment_items(item_bank)

		# Validate items with the compatibility gate (hard-fail on violations)
		compat_warnings = compat_gate.validate_assessment_items(
			assessment_items_tree
		)

		# Log compatibility warnings if any
		if self.verbose and compat_warnings:
			for warning in compat_warnings:
				print(f"Compatibility warning: {warning}")

		# Write metadata and manifest
		self.write_assessment_meta(item_count)
		self.write_manifest(item_count)

		# Create the ZIP file
		outfile = self.get_outfile_name('qti21-ultra', 'zip', outfile)
		with zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED) as zipf:
			# Add all files from output_dir
			for root, dirs, files in os.walk(self.output_dir):
				for file in files:
					full_path = os.path.join(root, file)
					relative_path = os.path.relpath(full_path, self.output_dir)
					zipf.write(full_path, relative_path)

			# Add the empty csfiles/home_dir/ directory as a zero-byte entry
			# (zipfile doesn't add empty dirs automatically)
			empty_dir_entry = "csfiles/home_dir/"
			if empty_dir_entry not in [info.filename for info in zipf.filelist]:
				zipf.writestr(empty_dir_entry, "")

		# Clean up temporary files
		self.clean_temp_files()

		if self.verbose:
			print(f"Saved {self.save_count} assessment items to {outfile}")

		return outfile

	#============================================
	def clean_temp_files(self):
		"""
		Delete temporary files created during package generation.
		"""
		if os.path.exists(self.output_dir):
			shutil.rmtree(self.output_dir)
