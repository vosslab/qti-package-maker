"""Blackboard pool export engine implementation."""

# Standard Library
import os
import time
import shutil
import zipfile

# QTI Package Maker
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.blackboard_export_zip import write_item
from qti_package_maker.engines.blackboard_export_zip import read_package
from qti_package_maker.engines.blackboard_export_zip import assessment_meta
from qti_package_maker.assessment_items.item_bank import ItemBank


#============================================
class EngineClass(base_engine.BaseEngine):
	"""
	Blackboard pool export engine that packages items into a ZIP bundle.

	Produces a .zip in the Blackboard pool export format (QTI-1.2-derived
	envelope + BB extensions) with the file layout:
	  imsmanifest.xml
	  res00001.dat ... res00007.dat  (pool wrapper + sidecars)
	  .bb-package-info
	  .bb-log-info
	  csfiles/          (empty directory, required by Blackboard)
	  res00001/         (empty directory, required by Blackboard)

	No .bb-package-sig is written; that signature is computed server-side.
	"""

	def __init__(self, package_name: str, verbose: bool = False) -> None:
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# Wire in the write_item dispatch module for this engine
		self.write_item = write_item
		# Confirm the module is the correct one for this engine folder
		self.validate_write_item_module()

	#============================================
	def read_items_from_file(self, infile: str, allow_mixed: bool = False) -> ItemBank:
		"""
		Read pool items from a Blackboard export ZIP.
		"""
		return read_package.read_items_from_file(infile, allow_mixed=allow_mixed)

	#============================================
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str:
		"""
		Build the Blackboard pool ZIP from the item bank.

		Steps:
		  1. process_item_bank: dispatch each item through write_item -> list of <item> Elements.
		  2. build_pool_wrapper: wrap items in questestinterop/assessment/section (res00002.dat).
		  3. build_manifest: emit imsmanifest.xml listing all resources.
		  4. Write each sidecar .dat (res00001, res00003..res00007).
		  5. Write .bb-package-info and .bb-log-info plain-text sidecars.
		  6. Create empty csfiles/ and res00001/ directory stubs in the temp dir.
		  7. Zip the entire temp dir tree.
		  8. Clean the temp dir.

		Args:
			item_bank: Iterable of assessment items.
			outfile: Optional output filename; generated from package_name if not provided.

		Returns:
			The path to the created ZIP file.
		"""
		# Derive a human-readable title for the pool header and manifest
		pool_title = assessment_meta.humanize_package_name(self.package_name)

		# Create a timestamped temp directory to collect the ZIP contents
		current_time = time.strftime("%H%M")
		temp_dir = os.path.join(
			os.getcwd(),
			f"BB-Export-{self.package_name}_package_{current_time}"
		)
		os.makedirs(temp_dir, exist_ok=True)

		# Step 1: render each item through the write_item dispatcher
		item_elements = self.process_item_bank(item_bank)

		# Step 2: build the pool wrapper (res00002.dat content)
		question_type = assessment_meta.first_question_type(item_elements)
		total_score = float(len(item_elements))
		pool_wrapper = assessment_meta.build_pool_wrapper(
			item_elements,
			pool_title,
			question_type,
			total_score,
		)
		pool_bytes = assessment_meta.serialize_xml(pool_wrapper)
		pool_path = os.path.join(temp_dir, assessment_meta.POOL_DAT_FILENAME)
		with open(pool_path, "wb") as f:
			f.write(pool_bytes)

		# Step 3: write imsmanifest.xml
		manifest_element = assessment_meta.build_manifest(pool_title)
		manifest_bytes = assessment_meta.serialize_xml(manifest_element)
		manifest_path = os.path.join(temp_dir, "imsmanifest.xml")
		with open(manifest_path, "wb") as f:
			f.write(manifest_bytes)

		# Step 4: write each fixed-content sidecar .dat
		for dat_filename in assessment_meta.sidecar_dat_filenames():
			sidecar_bytes = assessment_meta.build_sidecar_dat(dat_filename)
			sidecar_path = os.path.join(temp_dir, dat_filename)
			with open(sidecar_path, "wb") as f:
				f.write(sidecar_bytes)

		# Step 5: write .bb-package-info and .bb-log-info
		package_info_bytes = assessment_meta.build_bb_package_info(self.package_name)
		package_info_path = os.path.join(temp_dir, ".bb-package-info")
		with open(package_info_path, "wb") as f:
			f.write(package_info_bytes)

		log_info_bytes = assessment_meta.build_bb_log_info(self.package_name)
		log_info_path = os.path.join(temp_dir, ".bb-log-info")
		with open(log_info_path, "wb") as f:
			f.write(log_info_bytes)

		# Step 6: create empty directory stubs required by Blackboard
		# csfiles/ holds course file resources; res00001/ is the course-settings resource dir.
		os.makedirs(os.path.join(temp_dir, "csfiles"), exist_ok=True)
		os.makedirs(os.path.join(temp_dir, "res00001"), exist_ok=True)

		# Step 7: zip the temp directory tree into the output file
		outfile = self.get_outfile_name("blackboard_export_zip", "zip", outfile)
		with zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED) as zipf:
			for root, dirs, files in os.walk(temp_dir):
				for file in files:
					full_path = os.path.join(root, file)
					relative_path = os.path.relpath(full_path, temp_dir)
					zipf.write(full_path, relative_path)

			# Add the empty directory stubs as zero-byte entries
			# (zipfile does not add empty dirs automatically on os.walk)
			for empty_dir in ("csfiles/", "res00001/"):
				if empty_dir not in [info.filename for info in zipf.filelist]:
					zipf.writestr(empty_dir, "")

		# Step 8: clean up temp files
		if os.path.exists(temp_dir):
			shutil.rmtree(temp_dir)

		if self.verbose:
			print(f"Saved {len(item_elements)} items to {outfile}")

		return outfile
