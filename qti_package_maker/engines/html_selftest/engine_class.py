
# Standard Library
import base64
import random

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.html_selftest import write_item
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.assessment_items import item_types

class EngineClass(base_engine.BaseEngine):
	"""
	HTML self-test writer that renders a single random item per output file.

	Media policy: package. Every <img src> in the rendered fragment is
	resolved through media_assets, read from disk, and rewritten to a base64
	data:<mime>;base64,... URI (via media_assets.rewrite_html_srcs, writer
	output only) so the emitted fragment carries zero external image
	references and embeds cleanly at any mkdocs-material nav depth. The
	existing `.qti-selftest img` responsive CSS (html_functions.py) already
	renders data-URI images the same as file-referenced ones, so no CSS
	changes are needed here.
	"""
	media_policy = media_assets.POLICY_PACKAGE

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

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str:
		"""
		Write one randomly selected item to an HTML self-test file.
		"""
		outfile = self.get_outfile_name('selftest', 'html', outfile)
		item_cls, formatted_html_text = self._pick_and_render_random_item(item_bank)
		if formatted_html_text is not None:
			formatted_html_text = self._embed_images_as_data_uris(
				item_bank, item_cls, formatted_html_text)
		with open(outfile, "w") as f:
			# only one problem per file, only write one
			f.write(formatted_html_text)
		if self.verbose is True:
			print(f"Saved one assessment item to {outfile}")
		return outfile

	#==============
	def _pick_and_render_random_item(
				self, item_bank: ItemBank) -> tuple[item_types.BaseItem | None, str | None]:
		"""
		Shuffle the bank and render the first item whose write function succeeds.

		Mirrors BaseEngine.process_random_item_from_item_bank, but also returns
		the chosen item so its CRC can label itemized media warnings.
		"""
		if len(item_bank) == 0:
			print("No items to write out skipping")
			return None, None
		items = list(item_bank)
		random.shuffle(items)
		for item_cls in items:
			write_item_function = getattr(self.write_item, item_cls.item_type, None)
			if not write_item_function:
				print(f"Warning: No write function found for item type '{item_cls.item_type}'.")
				continue
			item_engine_data = write_item_function(item_cls)
			if item_engine_data is not None:
				return item_cls, item_engine_data
		return None, None

	#==============
	def _embed_images_as_data_uris(
				self, item_bank: ItemBank, item_cls: item_types.BaseItem, html_text: str) -> str:
		"""
		Resolve every <img src> in the rendered fragment and inline it as base64.

		Local raster/svg images are read from disk and embedded as a
		data:<mime>;base64,... URI. External URLs and pre-existing data URIs
		are left untouched; apply_media_policy emits the itemized edge-case
		warning for those (the single warning channel for every engine).
		"""
		src_list = media_assets.scan_html_for_assets(html_text)
		if not src_list:
			return html_text
		# resolve each distinct src once, keyed for the rewrite closure below
		asset_by_src = {}
		for src in src_list:
			if src not in asset_by_src:
				asset_by_src[src] = media_assets.resolve_asset(src, item_bank.media_base_dir)
		decision = media_assets.apply_media_policy(
			self.media_policy, list(asset_by_src.values()), self.name, item_cls.item_crc16)
		for warning in decision.warnings:
			print(warning)

		#----------------------------------------------------
		def _to_data_uri(src: str) -> str:
			asset = asset_by_src[src]
			if asset.kind != media_assets.KIND_LOCAL:
				# external references and pre-existing data URIs pass through untouched
				return src
			payload_bytes = asset.read_bytes()
			encoded_payload = base64.b64encode(payload_bytes).decode("ascii")
			return f"data:{asset.mime_type};base64,{encoded_payload}"

		rewritten_html = media_assets.rewrite_html_srcs(html_text, _to_data_uri)
		return rewritten_html
