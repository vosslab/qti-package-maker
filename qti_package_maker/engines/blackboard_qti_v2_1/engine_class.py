
# Standard Library
import os
import re
import time
import shutil

# Pip3 Library
import lxml.etree

# QTI Package Maker
from qti_package_maker.common import zip_writer
from qti_package_maker.common import media_assets
from qti_package_maker.common import qti_manifest
from qti_package_maker.engines import base_engine
from qti_package_maker.assessment_items import item_types
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.assessment_items.item_bank import CollectedAssets
from qti_package_maker.engines.blackboard_qti_v2_1 import write_item
from qti_package_maker.engines.blackboard_qti_v2_1 import assessment_meta
#from qti_package_maker.engines.blackboard_qti_v2_1 import item_xml_helpers

#==============
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

#==============
class EngineClass(base_engine.BaseEngine):
	"""
	Blackboard QTI 2.1 writer that packages items into a ZIP bundle.
	"""
	# Images are copied into the ZIP and their <img src> rewritten.
	media_policy = media_assets.POLICY_PACKAGE

	def __init__(self, package_name: str, verbose: bool=False) -> None:
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()
		# Setup Directories
		self._setup_directories()

	#==============
	def _setup_directories(self) -> None:
		"""
		Initialize output paths for the QTI 2.1 bundle.
		"""
		current_time = time.strftime("%H%M")
		self.output_dir = os.path.join(os.getcwd(), f"QTI21-{self.package_name}_package_{current_time}")
		#print(f"OUTPUT directory: {self.output_dir}")
		#self.assessment_base_name = "blackboard_qti21_items"
		self.assessment_base_name = "qti21_items"
		self.assessment_dir = os.path.join(self.output_dir, self.assessment_base_name)
		self.assessment_meta_file_path = os.path.join(self.assessment_dir, 'assessment_meta.xml')
		self.manifest_file_path = os.path.join(self.output_dir, "imsmanifest.xml")
		# Packaged (file-backed) image assets from the most recent write_assessment_items()
		# call; empty when the bank carries no local images.
		self.packaged_assets: list = []
		# Per-file dependency map (assessment file name -> its referenced assets)
		# for qti_manifest.generate_manifest's item_dependencies keyword.
		self.file_asset_dependencies: dict = {}

	#==============
	def read_package(self, infile: str) -> ItemBank:
		"""
		Read is not supported for this engine.
		"""
		raise NotImplementedError

	#==============
	def write_assessment_items(self, item_bank: ItemBank) -> list:
		"""
		Write each assessment item into its own Blackboard QTI 2.1 XML file.

		QTI 2.1 requires each assessment item to be stored in a separate XML file,
		unlike QTI 1.2, which allowed multiple items in one file.

		Returns:
			list: A list of relative paths to the saved assessment item XML files.
		"""
		if len(item_bank) == 0:
			print("No items to write out skipping")
			return

		# Stores the list of assessment item file paths
		assessment_file_name_list = []

		# Resolve every item's referenced images against the bank once. BB QTI 2.1
		# places images at the package ROOT (SAMPLES/blackboard_learn_classic-qti21_export);
		# assign_output_names() already gives collision-safe bare filenames, so no
		# subpath prefix is needed here (unlike Canvas's media/ subdir).
		collected = item_bank.collect_assets()
		local_assets = [asset for asset in collected.assets if asset.kind == media_assets.KIND_LOCAL]
		self.packaged_assets = local_assets
		self.file_asset_dependencies = {}

		self.save_count = 0
		item_number = 0
		# Render and write each item in one pass (rather than via process_item_bank)
		# so the item's own crc16 is available to look up its referenced images and
		# so each item's assets attach to the exact file name it ends up written to.
		for item_cls in item_bank:
			write_item_function = getattr(self.write_item, item_cls.item_type, None)
			if not write_item_function:
				print(f"Warning: No write function found for item type '{item_cls.item_type}'.")
				continue
			render_item_cls, local_item_assets = self._resolve_item_media(item_cls, collected)

			# The QTI 2.1 <assessmentItem> consists of four key parts:
			# - responseDeclaration: Defines expected answers
			# - outcomeDeclaration: Specifies scoring and outcome rules
			# - itemBody: Contains the actual question and options
			# - responseProcessing: Defines how the responses are evaluated
			assessment_item_etree = write_item_function(render_item_cls)
			if assessment_item_etree is None:
				print("No data to write out skipping")
				continue

			# Generate a unique filename for each assessment item XML
			item_number += 1
			item_file_name = f"item_{item_number:05d}.xml"

			# Generate file paths: relative path (for internal use) and global path (full path)
			item_relative_path = os.path.join(self.assessment_base_name, item_file_name)
			item_global_path = os.path.join(self.assessment_dir, item_file_name)

			# Store the relative path of the item file for reference
			assessment_file_name_list.append(item_relative_path)
			if local_item_assets:
				self.file_asset_dependencies[item_relative_path] = local_item_assets

			# Convert the modified assessment item to an XML string and write it
			assessment_item_xml_string = lxml.etree.tostring(
				assessment_item_etree,
				pretty_print=True,
				xml_declaration=True,
				encoding="UTF-8"
			)
			with open(item_global_path, "w", encoding="utf-8") as f:
				xml_text = assessment_item_xml_string.decode("utf-8")
				xml_text = _add_readability_spacing(xml_text)
				f.write(xml_text)
				self.save_count += 1

		# Write the packaged image bytes alongside the item XML files
		if local_assets:
			self.write_media_assets(local_assets)

		# Log the number of saved items and return the file list
		if self.verbose is True:
			print(f"Wrote {self.save_count} assessment items for {self.package_name}")
		return assessment_file_name_list

	#==============
	def _resolve_item_media(
				self,
				item_cls: item_types.BaseItem,
				collected: CollectedAssets) -> tuple:
		"""
		Apply the media policy to one item and return (item_to_render, local_assets).

		Raises on any data-URI reference (packaging needs a file to bundle).
		Prints itemized warnings for external/SVG references via the shared
		apply_media_policy channel. Returns the item unchanged, with an empty
		asset list, when it references no images.
		"""
		item_assets = collected.item_dependencies.get(item_cls.item_crc16, [])
		if not item_assets:
			return item_cls, []
		media_assets.raise_on_data_uri_assets(item_assets, self.name, item_cls.item_crc16)
		decision = media_assets.apply_media_policy(
			self.media_policy, item_assets, self.name, item_cls.item_crc16)
		for warning in decision.warnings:
			print(warning)
		local_item_assets = [asset for asset in item_assets if asset.kind == media_assets.KIND_LOCAL]
		if not local_item_assets:
			return item_cls, []
		# BB QTI 2.1 items live one directory under the package root (qti21_items/),
		# so a root-level image is reached with a single "../" (matches SAMPLES).
		src_map = {asset.src: f"../{asset.output_name}" for asset in local_item_assets}
		src_map_fn = media_assets.make_src_map_fn(src_map)
		render_item_cls = media_assets.rewrite_item_media(item_cls, src_map_fn)
		return render_item_cls, local_item_assets

	#==============
	def write_media_assets(self, assets: list) -> None:
		"""
		Write packaged image bytes to disk under the staged output directory.
		"""
		for asset in assets:
			dest_path = os.path.join(self.output_dir, asset.output_name)
			os.makedirs(os.path.dirname(dest_path), exist_ok=True)
			with open(dest_path, "wb") as file_pointer:
				file_pointer.write(asset.read_bytes())

	#==============
	def write_assessment_meta(self, assessment_file_name_list: list) -> None:
		# Generate imsmanifest.xml
		assessment_meta_etree = assessment_meta.generate_assessment_meta(self.package_name, assessment_file_name_list)
		assessment_meta_xml_string = lxml.etree.tostring(assessment_meta_etree,
			pretty_print=True, xml_declaration=True, encoding="UTF-8")
		with open(self.assessment_meta_file_path, "w", encoding="utf-8") as f:
			xml_text = assessment_meta_xml_string.decode("utf-8")
			xml_text = _add_readability_spacing(xml_text)
			f.write(xml_text)
		return

	#==============
	def write_manifest(self, assessment_file_name_list: list) -> None:
		# Generate imsmanifest.xml
		manifest_etree = qti_manifest.generate_manifest(self.package_name,
				assessment_file_name_list, version="2.1",
				assets=self.packaged_assets, item_dependencies=self.file_asset_dependencies)
		manifest_xml_string = lxml.etree.tostring(manifest_etree, pretty_print=True,
			xml_declaration=True, encoding="UTF-8")
		manifest_path = os.path.join(self.output_dir, "imsmanifest.xml")
		with open(manifest_path, "w", encoding="utf-8") as f:
			xml_text = manifest_xml_string.decode("utf-8")
			xml_text = _add_readability_spacing(xml_text)
			f.write(xml_text)
		return

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str=None) -> str:
		"""
		Write assessment XML, metadata, and manifest, then bundle the ZIP.
		"""
		# Validate media policy first: raise on any data-URI image BEFORE the
		# staging directories are created, so a rejected bank never leaks an
		# empty timestamped output dir into the current working directory.
		self.raise_on_unpackagable_media(item_bank)
		# Create necessary directories
		os.makedirs(self.output_dir, exist_ok=True)
		os.makedirs(self.assessment_dir, exist_ok=True)
		assessment_file_name_list = self.write_assessment_items(item_bank)
		self.write_assessment_meta(assessment_file_name_list)
		self.write_manifest(assessment_file_name_list)

		# Write the package to a ZIP file
		#zip_path = f"{self.package_name}.zip"
		outfile = self.get_outfile_name('qti21', 'zip', outfile)
		# Assemble the ZIP from the staged output directory via the shared writer
		archive_map = zip_writer.collect_directory(self.output_dir)
		zip_writer.build_zip(outfile, archive_map)
		self.clean_temp_files()
		if self.verbose is True:
			print(f"Saved {self.save_count} assessment items to {outfile}")
		return outfile

	#==============

	def clean_temp_files(self) -> None:
		"""
		Delete temporary files created during package generation.
		"""
		if os.path.exists(self.output_dir):
			shutil.rmtree(self.output_dir)
