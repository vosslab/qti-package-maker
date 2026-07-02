
# Standard Library
import functools

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.human_readable import write_item
from qti_package_maker.assessment_items import item_types
from qti_package_maker.assessment_items.item_bank import CollectedAssets
from qti_package_maker.assessment_items.item_bank import ItemBank

class EngineClass(base_engine.BaseEngine):
	"""
	Human-readable HTML writer that renders items into a preformatted page.

	Media policy: reference_warn. Every <img> tag is replaced with a readable
	inline description (name, alt text, source path) so a reviewer can see
	what image belongs where without this engine copying or embedding any
	file; each referenced image also gets one itemized warning.
	"""
	media_policy = media_assets.POLICY_REFERENCE_WARN

	def __init__(self, package_name: str, verbose: bool=False) -> None:
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()

	#==============
	def read_package(self, infile: str) -> None:
		"""
		Read is not supported for this engine.
		"""
		raise NotImplementedError

	#============================
	def write_html_header(self) -> str:
		"""
		Return the HTML header for the human-readable output.
		"""
		return (
			'<!DOCTYPE html>\n'
			'<html>\n<head>\n'
			'<meta charset="UTF-8">\n'
			'<style>\n'
			'  body {\n'
			'    background: white;\n'
			'    color: black;\n'
			'  }\n'
			'  @media (prefers-color-scheme: dark) {\n'
			'    body {\n'
			'      background: #121212;\n'
			'      color: #e0e0e0;\n'
			'    }\n'
			'  }\n'
			'</style>\n'
			'</head>\n<body>\n'
			'<pre>\n'
		)

	#============================
	def write_html_footer(self) -> str:
		"""
		Return the closing HTML tags for the human-readable output.
		"""
		return '</pre>\n</body>\n</html>\n'

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str | None:
		outfile = self.get_outfile_name('human', 'html', outfile)
		# Render through the shared loop; substitute each item's <img> tags with
		# a readable description on a CLONE BEFORE rendering (item_transform_fn),
		# since the pretty-printer strips any <img> tag still present at render.
		collected_assets = item_bank.collect_assets()
		item_transform_fn = functools.partial(self._describe_item_media, collected_assets)
		assessment_items_tree = self.process_item_bank(item_bank, item_transform_fn=item_transform_fn)
		if len(assessment_items_tree) == 0:
			return None
		# Write assessment items to the file
		with open(outfile, "w") as f:
			f.write(self.write_html_header())
			count = 0
			for item_num, assessment_text in enumerate(assessment_items_tree, start=1):
				f.write(f"{item_num}. ")
				f.write(assessment_text)
				count += 1
			f.write(self.write_html_footer())
		if self.verbose is True:
			print(f"Saved {count} assessment items to {outfile}")
		return outfile

	#==============
	def _describe_item_media(
				self,
				collected_assets: CollectedAssets,
				item_cls: item_types.BaseItem) -> item_types.BaseItem:
		"""
		Return the item to render, replacing `<img>` tags with descriptions.

		Pre-render transform for process_item_bank: the human-readable
		pretty-printer strips any `<img>` tag still present in the rendered
		text, so referenced images must already be a readable name + alt +
		source-path description by the time the write function runs. Items
		with no image dependencies are returned unchanged (no clone needed);
		the bank's stored item is never mutated.
		"""
		item_assets = collected_assets.item_dependencies.get(item_cls.item_crc16, [])
		if not item_assets:
			return item_cls
		decision = media_assets.apply_media_policy(
			self.media_policy, item_assets, self.name, item_cls.item_crc16)
		for warning in decision.warnings:
			print(warning)
		asset_by_src = {asset.src: asset for asset in item_assets}
		return write_item.clone_item_with_image_descriptions(item_cls, asset_by_src)
