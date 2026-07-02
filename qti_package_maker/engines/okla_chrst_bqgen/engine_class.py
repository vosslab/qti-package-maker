
# Standard Library
import functools

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.okla_chrst_bqgen import write_item
from qti_package_maker.engines.okla_chrst_bqgen import read_package
from qti_package_maker.assessment_items import item_types
from qti_package_maker.assessment_items.item_bank import CollectedAssets
from qti_package_maker.assessment_items.item_bank import ItemBank


class EngineClass(base_engine.BaseEngine):
	"""
	Okla CHRST BQGEN text engine with read and write support.

	Media policy: placeholder_warn. The okla_chrst_bqgen plain-text format
	carries no image markup, so every <img> tag is replaced with a readable
	`[image: name.ext]` placeholder and each referenced image gets one
	itemized warning.
	"""
	media_policy = media_assets.POLICY_PLACEHOLDER_WARN

	def __init__(self, package_name: str, verbose: bool = False) -> None:
		super().__init__(package_name, verbose)
		self.write_item = write_item
		self.validate_write_item_module()

	#============================================
	def read_items_from_file(self, infile: str, allow_mixed: bool = False) -> ItemBank:
		"""
		Read okla_chrst_bqgen text files into an ItemBank.
		"""
		return read_package.read_items_from_file(infile, allow_mixed=allow_mixed)

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str | None:
		"""
		Write the item bank to an okla_chrst_bqgen formatted text file.
		"""
		outfile = self.get_outfile_name('okla', 'txt', outfile)
		# Render through the shared loop; replace each item's <img> tags with
		# their readable placeholder AFTER the plain-text render (post_render_fn).
		collected_assets = item_bank.collect_assets()
		post_render_fn = functools.partial(self._replace_images_with_placeholders, collected_assets)
		assessment_items_tree = self.process_item_bank(item_bank, post_render_fn=post_render_fn)
		if len(assessment_items_tree) == 0:
			return None
		with open(outfile, "w") as f:
			count = 0
			for item_number, assessment_text in enumerate(assessment_items_tree, start=1):
				f.write(assessment_text)
				if not assessment_text.endswith("\n"):
					f.write("\n")
				count += 1
		if self.verbose:
			print(f"Saved {count} assessment items to {outfile}")
		return outfile

	#==============
	def _replace_images_with_placeholders(
				self,
				collected_assets: CollectedAssets,
				item_cls: item_types.BaseItem,
				item_text: str) -> str:
		"""
		Replace the rendered item's `<img>` tags with `[image: name.ext]` text.

		Post-render transform for process_item_bank: keyed on the original item
		so it can resolve that item's referenced images, then substituted into
		the already-rendered plain text (this format has no image markup channel).
		"""
		item_assets = collected_assets.item_dependencies.get(item_cls.item_crc16, [])
		if item_assets:
			decision = media_assets.apply_media_policy(
				self.media_policy, item_assets, self.name, item_cls.item_crc16)
			for warning in decision.warnings:
				print(warning)
			item_text = write_item.replace_images_with_placeholders(item_text, decision.placeholders)
		return item_text
