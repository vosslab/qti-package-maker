
# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.bbq_text_upload import write_item
from qti_package_maker.engines.bbq_text_upload import read_package
from qti_package_maker.assessment_items.item_bank import ItemBank

class EngineClass(base_engine.BaseEngine):
	"""
	Blackboard BBQ text upload engine with read and write support.

	Uses the inherited reference_warn media_policy: BBQ text upload has no
	channel to carry image files, so <img> tags are kept verbatim in the
	written text and each referenced image gets one itemized warning.
	"""
	def __init__(self, package_name: str, verbose: bool = False) -> None:
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()

	#==============
	def read_items_from_file(self, infile: str, allow_mixed: bool = False) -> ItemBank:
		"""
		Read a BBQ text upload file and return an ItemBank.
		"""
		new_item_bank = read_package.read_items_from_file(infile, allow_mixed=allow_mixed)
		return new_item_bank

	#==============
	def _warn_about_item_media(self, item_bank: ItemBank) -> None:
		"""
		Print one itemized warning per image referenced by the item bank.

		BBQ text upload cannot transport image files, so every engine-referenced
		image routes through the declared media_policy (reference_warn) and
		surfaces via the single media_assets.apply_media_policy warning channel.
		"""
		collected_assets = item_bank.collect_assets()
		for item_crc16, item_assets in collected_assets.item_dependencies.items():
			decision = media_assets.apply_media_policy(
				self.media_policy, item_assets, self.name, item_crc16)
			for warning in decision.warnings:
				print(warning)

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str:
		"""
		Write the item bank to a BBQ text upload file.
		"""
		outfile = self.get_outfile_name('bbq', 'txt', outfile)
		# emit the itemized image warnings before rendering item text
		self._warn_about_item_media(item_bank)
		assessment_items_tree = self.process_item_bank(item_bank)
		# Write assessment items to the file
		with open(outfile, "w") as f:
			count = 0
			for formatted_bbq_text in assessment_items_tree:
				# no inner newlines allowed
				formatted_bbq_text = formatted_bbq_text.replace('\n', ' ').strip()
				# Ensure each item is on a new line
				f.write(formatted_bbq_text + "\n")
				count += 1
		if self.verbose is True:
			print(f"Saved {count} assessment items to {outfile}")
		return outfile
