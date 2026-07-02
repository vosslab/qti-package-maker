"""Blackboard pool export engine implementation."""

# Standard Library
import os
import time
import shutil
import functools
import dataclasses
import collections.abc

# QTI Package Maker
from qti_package_maker.common import zip_writer
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.blackboard_export_zip import write_item
from qti_package_maker.engines.blackboard_export_zip import common_xml
from qti_package_maker.engines.blackboard_export_zip import read_package
from qti_package_maker.engines.blackboard_export_zip import assessment_meta
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.assessment_items.item_bank import CollectedAssets


#============================================
@dataclasses.dataclass
class _ImageEmbedPlan:
	"""
	The csfiles image-embedding plan for one save_package call.

	src_map_fn rewrites each in-content `<img src>` to its minted csfiles token
	before an item is rendered; link_entries are the (parent_id, resource_id)
	pairs for res00005.dat; home_dir_files are the (filename, bytes) pairs
	written under csfiles/home_dir/ (each image contributes a binary plus its
	LOM sidecar). An empty plan (no local images) carries the identity mapper,
	no link entries, and no files, so the no-image write path is unchanged.
	"""
	src_map_fn: collections.abc.Callable[[str], str]
	link_entries: list[tuple[str, str]]
	home_dir_files: list[tuple[str, bytes]]


#============================================
def _identity_src_map(old_src: str) -> str:
	"""Return old_src unchanged; used when a bank carries no local images."""
	return old_src


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
	  csfiles/home_dir/__xid-<n>_1.<ext>      (embedded item images)
	  csfiles/home_dir/__xid-<n>_1.<ext>.xml  (per-image LOM sidecars)
	  res00001/         (empty directory, required by Blackboard)

	When the bank carries no images, csfiles/ ships as an empty directory marker
	(the historical layout). No .bb-package-sig is written; that signature is
	computed server-side.

	Image support: item images are embedded through Blackboard's
	proprietary, manifest-untracked "csfiles" mechanism. Each local `<img src>`
	is rewritten to an `@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1`
	token in the pool body; its bytes are written to csfiles/home_dir/, a LOM
	sidecar recovers the original filename, and a res00005.dat CSResourceLinks
	entry cross-references the xid. This is the exact inverse of read_package.py,
	so write -> read round-trips the image bytes and the `<img src>` references
	(see assessment_meta's csfiles image-embedding section for the wiring, pinned
	from SAMPLES/blackboard_learn_classic-bb_export).

	Hotspot images (the QTI `<matapplication>` + manifest `<file>` path) are NOT
	written: no item_types class models a hotspot response area, so no bank item
	can carry a `<matapplication>`. The reader still imports the hotspot
	mechanism; this write/read asymmetry is intentional, not missing work.

	Data URI images raise media_assets.MediaPolicyError instead of packaging:
	this engine writes files, and a data URI carries no file for it to embed.
	External URLs keep warn+verbatim and SVGs keep package+warn.
	"""

	# Images are embedded via the csfiles mechanism and their <img src> rewritten
	# to bbcswebdav xid tokens; external URLs are left in the body with an
	# itemized warning through the shared media-policy channel, and data URIs
	# raise media_assets.MediaPolicyError (this engine writes files, so it cannot
	# package a data URI).
	media_policy = media_assets.POLICY_PACKAGE

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
	def save_package(self, item_bank: ItemBank, outfile: str | None = None) -> str:
		"""
		Build the Blackboard pool ZIP from the item bank.

		Steps:
		  0. Plan csfiles image embedding (mint xids, build the src rewrite map,
		     LOM sidecars, and CSResourceLinks entries).
		  1. Render each item, rewriting <img src> to its csfiles token -> list of
		     <item> Elements.
		  2. build_pool_wrapper: wrap items in questestinterop/assessment/section (res00002.dat).
		  3. build_manifest: emit imsmanifest.xml listing all resources.
		  4. Write each fixed sidecar .dat (res00001, res00003, res00004, res00006,
		     res00007), then res00005.dat CSResourceLinks (populated per image).
		  5. Write .bb-package-info and .bb-log-info plain-text sidecars.
		  6. Write embedded image binaries + LOM sidecars under csfiles/home_dir/;
		     res00001/ (and csfiles/ when imageless) ship as empty-dir markers.
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

		# Step 0: plan csfiles image embedding (empty plan when no local images).
		# This validates media policy and RAISES on data-URI images, so it runs
		# BEFORE the staging directory is created. Validation first, side effects
		# second: a rejected bank never leaves a leaked staging dir behind.
		image_plan = self._plan_image_embedding(item_bank)

		# Create a timestamped temp directory to collect the ZIP contents
		current_time = time.strftime("%H%M")
		temp_dir = os.path.join(
			os.getcwd(),
			f"BB-Export-{self.package_name}_package_{current_time}"
		)
		os.makedirs(temp_dir, exist_ok=True)

		# Step 1: render each item, rewriting <img src> to its csfiles token
		item_elements = self._render_items(item_bank, image_plan.src_map_fn)

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

		# Step 4: write each fixed-content sidecar .dat (res00005 is written
		# separately below, since it carries per-image CSResourceLinks content)
		for dat_filename in assessment_meta.sidecar_dat_filenames():
			sidecar_bytes = assessment_meta.build_sidecar_dat(dat_filename)
			sidecar_path = os.path.join(temp_dir, dat_filename)
			with open(sidecar_path, "wb") as f:
				f.write(sidecar_bytes)

		# Step 4b: write res00005.dat (CSResourceLinks). Populated with one entry
		# per embedded image; an empty list yields the minimal empty-list body.
		csresourcelinks_bytes = assessment_meta.build_csresourcelinks_dat(image_plan.link_entries)
		csresourcelinks_path = os.path.join(temp_dir, assessment_meta.CSRESOURCELINKS_DAT_FILENAME)
		with open(csresourcelinks_path, "wb") as f:
			f.write(csresourcelinks_bytes)

		# Step 5: write .bb-package-info and .bb-log-info
		package_info_bytes = assessment_meta.build_bb_package_info(self.package_name)
		package_info_path = os.path.join(temp_dir, ".bb-package-info")
		with open(package_info_path, "wb") as f:
			f.write(package_info_bytes)

		log_info_bytes = assessment_meta.build_bb_log_info(self.package_name)
		log_info_path = os.path.join(temp_dir, ".bb-log-info")
		with open(log_info_path, "wb") as f:
			f.write(log_info_bytes)

		# Step 6: res00001/ is always an empty course-settings resource dir stub.
		os.makedirs(os.path.join(temp_dir, "res00001"), exist_ok=True)

		# Step 6b: write embedded image binaries and their LOM sidecars under
		# csfiles/home_dir/ (manifest-untracked; the reader finds them via the
		# body xid tokens and res00005.dat).
		self._write_image_files(temp_dir, image_plan.home_dir_files)

		# Step 7: zip the temp directory tree into the output file via the shared
		# writer. res00001/ is always an empty-directory marker; csfiles/ ships as
		# an empty marker only when no images were embedded (otherwise its
		# home_dir/ files already create the directory).
		outfile = self.get_outfile_name("blackboard_export_zip", "zip", outfile)
		empty_dirs = ["res00001/"]
		if not image_plan.home_dir_files:
			empty_dirs.append("csfiles/")
		archive_map = zip_writer.collect_directory(temp_dir)
		zip_writer.build_zip(outfile, archive_map, empty_dirs=empty_dirs)

		# Step 8: clean up temp files
		if os.path.exists(temp_dir):
			shutil.rmtree(temp_dir)

		if self.verbose:
			print(f"Saved {len(item_elements)} items to {outfile}")

		return outfile

	#============================================
	def _render_items(
				self,
				item_bank: ItemBank,
				src_map_fn: collections.abc.Callable[[str], str]) -> list:
		"""
		Render every item through the shared loop with `<img src>` rewriting.

		Rewrites each item's `<img src>` values to their csfiles tokens on a deep
		copy BEFORE rendering (item_transform_fn), so the pool body carries the
		tokens while the stored bank item is untouched. With the identity mapper
		(no images) the copy is byte-equivalent to the original, so the no-image
		path is unchanged.

		Args:
			item_bank: The bank whose items are rendered, in bank order.
			src_map_fn: Maps an in-content src to its csfiles token.

		Returns:
			The list of built `<item>` elements, in bank order.
		"""
		item_transform_fn = functools.partial(media_assets.rewrite_item_media, src_map_fn=src_map_fn)
		return self.process_item_bank(item_bank, item_transform_fn=item_transform_fn)

	#============================================
	def _plan_image_embedding(self, item_bank: ItemBank) -> _ImageEmbedPlan:
		"""
		Resolve the bank's images and plan the csfiles embedding.

		Scans every item's HTML once (ItemBank.collect_assets), surfaces the
		shared media-policy warnings for edge content (external/data-uri/SVG),
		then mints one unique xid per local file-backed image. For each image it
		records the src->token rewrite, the csfiles binary and LOM-sidecar bytes,
		and the CSResourceLinks entry. Non-local assets (external URLs, data URIs)
		are left in the body verbatim under the package policy and never bundled.

		Args:
			item_bank: The bank to package.

		Returns:
			An _ImageEmbedPlan; an empty plan when the bank carries no local images.
		"""
		collected = item_bank.collect_assets()
		local_assets = [
			asset for asset in collected.assets
			if asset.kind == media_assets.KIND_LOCAL
		]
		# Surface external/data-uri/SVG warnings through the one shared channel.
		self._warn_on_media_policy(item_bank, collected)
		if not local_assets:
			return _ImageEmbedPlan(_identity_src_map, [], [])
		# Mint a unique xid per asset. collect_assets returns assets sorted by src,
		# so xid assignment is deterministic across runs.
		src_to_token: dict[str, str] = {}
		xid_by_src: dict[str, int] = {}
		home_dir_files: list[tuple[str, bytes]] = []
		for index, asset in enumerate(local_assets, start=1):
			xid_number = index
			xid_by_src[asset.src] = xid_number
			src_to_token[asset.src] = assessment_meta.csfiles_src_value(xid_number)
			# The binary keeps the asset's real extension; the LOM sidecar recovers
			# the collision-safe output_name so read rewrites src back to it.
			extension = os.path.splitext(asset.output_name)[1]
			binary_name = assessment_meta.csfiles_binary_name(xid_number, extension)
			home_dir_files.append((binary_name, asset.read_bytes()))
			resource_id = assessment_meta.make_resource_id(xid_number)
			sidecar_bytes = assessment_meta.build_lom_sidecar(resource_id, asset.output_name)
			home_dir_files.append((f"{binary_name}.xml", sidecar_bytes))
		link_entries = self._build_link_entries(item_bank, collected, xid_by_src)

		src_map_fn = media_assets.make_src_map_fn(src_to_token)
		return _ImageEmbedPlan(src_map_fn, link_entries, home_dir_files)

	#============================================
	def _warn_on_media_policy(self, item_bank: ItemBank, collected: CollectedAssets) -> None:
		"""
		Raise on data URIs and print the shared media-policy warnings otherwise.

		Under POLICY_PACKAGE this surfaces only edge content (external URLs, data
		URIs, SVGs); first-class raster images bundle silently. Data URIs cannot be
		bundled as a file by a file-packaging engine, so they raise instead of
		warning; external URLs keep warn+verbatim and SVGs keep package+warn.

		Args:
			item_bank: The bank being packaged.
			collected: The bank's collected assets and per-item dependency map.

		Raises:
			media_assets.MediaPolicyError: an item references a data URI image.
		"""
		for item_cls in item_bank:
			item_assets = collected.item_dependencies.get(item_cls.item_crc16, [])
			if not item_assets:
				continue
			media_assets.raise_on_data_uri_assets(item_assets, self.name, item_cls.item_crc16)
			decision = media_assets.apply_media_policy(
				self.media_policy, item_assets, self.name, item_cls.item_crc16)
			for warning in decision.warnings:
				print(warning)

	#============================================
	def _build_link_entries(
				self,
				item_bank: ItemBank,
				collected: CollectedAssets,
				xid_by_src: dict[str, int]) -> list[tuple[str, str]]:
		"""
		Build the CSResourceLinks (parent_id, resource_id) entries, one per image.

		Each entry's parentId is the deterministic asi id of the FIRST item (in
		bank order) that references the image, matching real Blackboard exports
		where each xid names one owning item. The parentId is derived with
		common_xml.make_item_asi_object_id, the SAME helper that stamps each
		item's <bbmd_asi_object_id>, so the parent always resolves within the
		package (a mismatch makes Learn drop the link and the embedded image).

		Args:
			item_bank: The bank being packaged, iterated in bank order.
			collected: The bank's per-item dependency map.
			xid_by_src: The minted xid integer per local image src.

		Returns:
			One (parent_id, resource_id) pair per minted image, ordered by src.
		"""
		# First item that references each image owns it (bank order = first-use).
		parent_by_src: dict[str, str] = {}
		for item_cls in item_bank:
			for asset in collected.item_dependencies.get(item_cls.item_crc16, []):
				if asset.src in xid_by_src and asset.src not in parent_by_src:
					parent_by_src[asset.src] = common_xml.make_item_asi_object_id(
						item_cls.item_crc16)
		# Emit entries in the same deterministic src order the xids were minted in.
		link_entries = []
		for src in sorted(xid_by_src):
			resource_id = assessment_meta.make_resource_id(xid_by_src[src])
			link_entries.append((parent_by_src[src], resource_id))
		return link_entries

	#============================================
	def _write_image_files(self, temp_dir: str, home_dir_files: list[tuple[str, bytes]]) -> None:
		"""
		Write embedded image binaries and LOM sidecars under csfiles/home_dir/.

		Args:
			temp_dir: The staging directory the ZIP is built from.
			home_dir_files: (filename, bytes) pairs to write into csfiles/home_dir/.
		"""
		if not home_dir_files:
			return
		home_dir_path = os.path.join(temp_dir, assessment_meta.CSFILES_HOME_SUBDIR)
		os.makedirs(home_dir_path, exist_ok=True)
		for filename, file_bytes in home_dir_files:
			with open(os.path.join(home_dir_path, filename), "wb") as f:
				f.write(file_bytes)
