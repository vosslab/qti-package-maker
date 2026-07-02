
# Standard Library
import os
import re
import time
import shutil
import functools

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
from qti_package_maker.engines.canvas_qti_v1_2 import write_item
from qti_package_maker.engines.canvas_qti_v1_2 import assessment_meta
from qti_package_maker.engines.canvas_qti_v1_2 import item_xml_helpers

# Common Cartridge convention: packaged images live under media/ at the
# package root (text2qti prior art; no real Canvas sample confirms it yet).
CANVAS_MEDIA_SUBDIR = "media"

# The two <img src> token shapes gate A will probe on a real Canvas
# import: a plain package-root-relative path, or Canvas's own $IMS-CC-FILEBASE$
# token. Selectable programmatically (constructor kwarg / instance attribute),
# never via argparse, so probe kits can build both variants.
CANVAS_SRC_VARIANT_RELATIVE = "relative"
CANVAS_SRC_VARIANT_FILEBASE = "filebase"
VALID_CANVAS_SRC_VARIANTS = (CANVAS_SRC_VARIANT_RELATIVE, CANVAS_SRC_VARIANT_FILEBASE)

#==============
def _add_readability_spacing(xml_text: str) -> str:
	"""
	Add blank lines between major QTI 1.2 XML blocks for easier manual inspection.
	"""
	xml_text = re.sub(r"(</itemmetadata>\n)(\s*<presentation>)", r"\1\n\2", xml_text)
	xml_text = re.sub(r"(</presentation>\n)(\s*<resprocessing>)", r"\1\n\2", xml_text)
	xml_text = re.sub(r"(</item>\n)(\s*<item\b)", r"\1\n\2", xml_text)
	if not xml_text.endswith("\n"):
		xml_text += "\n"
	return xml_text

#==============
class EngineClass(base_engine.BaseEngine):
	"""
	Canvas QTI 1.2 writer that packages items into a ZIP bundle.
	"""
	# Images are copied into the ZIP and their <img src> rewritten.
	media_policy = media_assets.POLICY_PACKAGE

	def __init__(
				self,
				package_name: str,
				verbose: bool = False,
				canvas_src_variant: str = CANVAS_SRC_VARIANT_RELATIVE) -> None:
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()
		# Setup Directories
		self._setup_directories()
		if canvas_src_variant not in VALID_CANVAS_SRC_VARIANTS:
			raise ValueError(
				f"Invalid canvas_src_variant '{canvas_src_variant}'; valid: {VALID_CANVAS_SRC_VARIANTS}"
			)
		# A plain instance attribute (not argparse) so probe kits can flip it
		# after construction too: engine.canvas_src_variant = "filebase".
		self.canvas_src_variant = canvas_src_variant

	#==============
	def _setup_directories(self) -> None:
		"""
		Initialize output paths for the QTI 1.2 bundle.
		"""
		current_time = time.strftime("%H%M")
		self.output_dir = os.path.join(os.getcwd(), f"QTI12-{self.package_name}_package_{current_time}")
		#print(f"OUTPUT directory: {self.output_dir}")
		# Create necessary directories
		self.assessment_base_name = "canvas_qti12_questions"
		self.assessment_dir = os.path.join(self.output_dir, self.assessment_base_name)
		self.assessment_items_file_name = self.assessment_base_name + ".xml"
		self.assessment_items_base_path = os.path.join(self.assessment_base_name, self.assessment_items_file_name)
		self.assessment_items_file_path = os.path.join(self.output_dir, self.assessment_items_base_path)
		self.assessment_meta_file_path = os.path.join(self.assessment_dir, 'assessment_meta.xml')
		self.manifest_file_path = os.path.join(self.output_dir, "imsmanifest.xml")
		# Packaged (file-backed) image assets from the most recent write_assessment_items()
		# call; empty when the bank carries no local images.
		self.packaged_assets: list = []

	#==============
	def read_package(self, infile: str) -> ItemBank:
		"""
		Read is not supported for this engine.
		"""
		raise NotImplementedError

	#==============
	def write_assessment_items(self, item_bank: ItemBank) -> None:
		"""
		Write all assessment items into a single Canvas QTI 1.2 XML file.
		"""
		if len(item_bank) == 0:
			print("No items to write out skipping")
			return
		# Step 1: Create <section> to hold assessment items
		section_level_etree = lxml.etree.Element("section", ident="root_section")

		# Step 1b: Resolve every item's referenced images against the bank once,
		# then assign the Common Cartridge media/ subpath (the shared manifest keeps
		# its old shape unless we pass output_name WITH the subpath).
		collected = item_bank.collect_assets()
		local_assets = [asset for asset in collected.assets if asset.kind == media_assets.KIND_LOCAL]
		for asset in local_assets:
			asset.output_name = f"{CANVAS_MEDIA_SUBDIR}/{asset.output_name}"
		self.packaged_assets = local_assets

		# Step 2: Append each <item> (assessment item), rewriting <img src> first.
		# The <img src> rewrite is a PRE-render transform (item_transform_fn) that
		# returns a rewritten copy of each item that references local images.
		self.save_count = 0
		item_transform_fn = functools.partial(self._resolve_item_media, collected=collected)
		assessment_items_tree = self.process_item_bank(item_bank, item_transform_fn=item_transform_fn)
		for assessment_item_etree in assessment_items_tree:
			self.save_count += 1
			section_level_etree.append(assessment_item_etree)

		# Step 2b: Write the packaged image bytes alongside the item XML
		if local_assets:
			self.write_media_assets(local_assets)

		# Step 3: Create <assessment> and append <section>
		assessment_level_etree = lxml.etree.Element("assessment", ident="root_assessment", title=self.package_name)
		assessment_level_etree.append(section_level_etree)

		# Step 4: Create XML root <questestinterop> and append <assessment>
		assessment_items_file_xml_root = item_xml_helpers.create_assessment_items_file_xml_header()
		assessment_items_file_xml_root.append(assessment_level_etree)

		# Step 5: Save final XML to file
		assessment_items_xml_string = lxml.etree.tostring(
			assessment_items_file_xml_root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
		)

		with open(self.assessment_items_file_path, "w", encoding="utf-8") as f:
			xml_text = assessment_items_xml_string.decode("utf-8")
			xml_text = _add_readability_spacing(xml_text)
			f.write(xml_text)

		# Step 6: Log & return filename
		if self.verbose is True:
			print(f"Wrote {self.save_count} assessment items to {self.assessment_items_base_path}")
		return

	#==============
	def _resolve_item_media(
				self,
				item_cls: item_types.BaseItem,
				collected: CollectedAssets) -> item_types.BaseItem:
		"""
		Apply the media policy to one item and return the item to render.

		Raises on any data-URI reference (packaging needs a file to bundle).
		Prints itemized warnings for external/SVG references via the shared
		apply_media_policy channel. Returns a rewritten copy when the item
		references any local (file-backed) image, otherwise the item unchanged.
		"""
		item_assets = collected.item_dependencies.get(item_cls.item_crc16, [])
		if not item_assets:
			return item_cls
		media_assets.raise_on_data_uri_assets(item_assets, self.name, item_cls.item_crc16)
		decision = media_assets.apply_media_policy(
			self.media_policy, item_assets, self.name, item_cls.item_crc16)
		for warning in decision.warnings:
			print(warning)
		src_map = {
			asset.src: self._canvas_src_token(asset)
			for asset in item_assets if asset.kind == media_assets.KIND_LOCAL
		}
		if not src_map:
			return item_cls
		src_map_fn = media_assets.make_src_map_fn(src_map)
		return media_assets.rewrite_item_media(item_cls, src_map_fn)

	#==============
	def _canvas_src_token(self, asset: media_assets.MediaAsset) -> str:
		"""
		Build the <img src> token for a packaged asset per canvas_src_variant.
		"""
		if self.canvas_src_variant == CANVAS_SRC_VARIANT_FILEBASE:
			# Canvas's own export convention (matches text2qti prior art)
			return f"$IMS-CC-FILEBASE$/{asset.output_name}"
		# package-root-relative path from the item file's own directory
		# (canvas_qti12_questions/) up to the package root
		return f"../{asset.output_name}"

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
	def write_assessment_meta(self) -> None:
		# Generate imsmanifest.xml
		assessment_meta_etree = assessment_meta.generate_assessment_meta(self.package_name)
		assessment_meta_xml_string = lxml.etree.tostring(assessment_meta_etree,
			pretty_print=True, xml_declaration=True, encoding="UTF-8")
		with open(self.assessment_meta_file_path, "w", encoding="utf-8") as f:
			xml_text = assessment_meta_xml_string.decode("utf-8")
			xml_text = _add_readability_spacing(xml_text)
			f.write(xml_text)
		return

	#==============
	def write_manifest(self) -> None:
		# Generate imsmanifest.xml
		file_list = [self.assessment_items_base_path, ]
		item_dependencies = None
		if self.packaged_assets:
			item_dependencies = {self.assessment_items_base_path: self.packaged_assets}
		manifest_etree = qti_manifest.generate_manifest(
			self.package_name, file_list, version="1.2",
			assets=self.packaged_assets, item_dependencies=item_dependencies)
		manifest_xml_string = lxml.etree.tostring(manifest_etree, pretty_print=True,
			xml_declaration=True, encoding="UTF-8")
		with open(self.manifest_file_path, "w", encoding="utf-8") as f:
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
		# Items first: write_manifest() reads self.packaged_assets, which
		# write_assessment_items() populates from item_bank.collect_assets().
		self.write_assessment_items(item_bank)
		self.write_assessment_meta()
		self.write_manifest()

		# Write the package to a ZIP file
		#zip_path = f"{self.package_name}-qti_v1_2.zip"
		#zip_path = f"{self.package_name}.zip"
		outfile = self.get_outfile_name('qti12', 'zip', outfile)
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
