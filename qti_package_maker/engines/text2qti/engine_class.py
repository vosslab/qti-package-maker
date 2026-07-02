
# Standard Library
import os
import functools

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.text2qti import write_item
from qti_package_maker.engines.text2qti import read_package
from qti_package_maker.assessment_items import item_types
from qti_package_maker.assessment_items.item_bank import CollectedAssets
from qti_package_maker.assessment_items.item_bank import ItemBank

class EngineClass(base_engine.BaseEngine):
	"""
	Text2qti engine for the plain-text format used by the text2qti reader and writer.
	Supports reading and writing text2qti files.

	Media policy: reference_warn. Every <img src> is rewritten to text2qti's own
	markdown image syntax `![alt](media/name.png)` and the underlying bytes are
	copied into a `media/` folder beside the output file, so the reference stays
	readable and this engine's own reader re-resolves it back into a normal
	`<img src>` item field (no `asset:` scheme is ever stored in item content).
	"""
	media_policy = media_assets.POLICY_REFERENCE_WARN

	#============================================
	def __init__(self, package_name: str, verbose: bool = False) -> None:
		"""
		Initializes the text2qti engine with the package name.
		Args:
			package_name (str): Name of the package being processed.
			verbose (bool): Whether to print debug information.
		"""
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()

	#============================================
	def read_items_from_file(self, infile: str, allow_mixed: bool = False) -> ItemBank:
		"""
		Read text2qti questions from a text file and return an ItemBank.
		"""
		new_item_bank = read_package.read_items_from_file(infile, allow_mixed=allow_mixed)
		return new_item_bank

	#============================================
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str:
		"""
		Write the item bank to a text2qti-formatted text file.

		Referenced local images are copied to a `media/` folder beside outfile
		and every <img> tag is rewritten to `![alt](media/name.png)`.
		"""
		outfile = self.get_outfile_name('text2qti', 'txt', outfile)
		assessment_items_tree = self._render_items_with_media(item_bank, outfile)
		# Write assessment items to the file
		with open(outfile, "w") as f:
			count = 0
			for item_text in assessment_items_tree:
				f.write(item_text)
				count += 1
		if self.verbose is True:
			print(f"Saved {count} assessment items to {outfile}")
		return outfile

	#============================================
	def _render_items_with_media(self, item_bank: ItemBank, outfile: str) -> list:
		"""
		Render every item, copying any referenced local images beside outfile
		and rewriting their <img> tags to markdown image syntax.
		"""
		# The image copy + markdown rewrite is a POST-render transform keyed on
		# the original item; it closes over the media/ dir and the copied-name
		# set so bytes are written once across the whole bank.
		collected_assets = item_bank.collect_assets()
		media_dir = os.path.join(os.path.dirname(outfile), "media")
		copied_output_names = set()
		post_render_fn = functools.partial(
			self._replace_images_with_markdown, collected_assets, media_dir, copied_output_names)
		return self.process_item_bank(item_bank, post_render_fn=post_render_fn)

	#============================================
	def _replace_images_with_markdown(
				self,
				collected_assets: CollectedAssets,
				media_dir: str,
				copied_output_names: set,
				item_cls: item_types.BaseItem,
				item_text: str) -> str:
		"""
		Rewrite the rendered item's `<img>` tags to markdown image syntax.

		Post-render transform for process_item_bank: keyed on the original item
		so it can resolve that item's referenced images, copy their bytes into
		media_dir once, and rewrite each `<img>` tag to `![alt](media/name.png)`.
		"""
		item_assets = collected_assets.item_dependencies.get(item_cls.item_crc16, [])
		if item_assets:
			decision = media_assets.apply_media_policy(
				self.media_policy, item_assets, self.name, item_cls.item_crc16)
			for warning in decision.warnings:
				print(warning)
			markdown_target_by_src = self._copy_and_map_targets(
				item_assets, media_dir, copied_output_names)
			item_text = write_item.replace_images_with_markdown(item_text, markdown_target_by_src)
		return item_text

	#============================================
	def _copy_and_map_targets(
				self, item_assets: list, media_dir: str, copied_output_names: set) -> dict:
		"""
		Copy each local asset's bytes into media_dir once and map its src to
		the "media/<output_name>" markdown link target. External and data-uri
		assets have no output_name; they map to their original src unchanged.
		"""
		markdown_target_by_src = {}
		for asset in item_assets:
			if asset.kind != media_assets.KIND_LOCAL:
				markdown_target_by_src[asset.src] = asset.src
				continue
			if asset.output_name not in copied_output_names:
				os.makedirs(media_dir, exist_ok=True)
				dest_path = os.path.join(media_dir, asset.output_name)
				with open(dest_path, "wb") as dest_file:
					dest_file.write(asset.read_bytes())
				copied_output_names.add(asset.output_name)
			markdown_target_by_src[asset.src] = f"media/{asset.output_name}"
		return markdown_target_by_src
