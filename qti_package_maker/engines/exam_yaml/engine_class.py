
# Standard Library
import datetime

# Pip3 Library
import yaml

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.exam_yaml import write_item
from qti_package_maker.assessment_items.item_bank import ItemBank

class EngineClass(base_engine.BaseEngine):
	"""
	Write-only engine that exports an ItemBank to exam YAML format.

	Exam YAML is a print-oriented format for generating ODT exams.
	It is intentionally lossy: answer keys, scoring metadata, and
	section structure are not preserved.

	Media policy: reference_warn. `write_item.py` writes `question_text`
	verbatim into the YAML `statement` field, so any `<img>` tag is kept
	unchanged; each referenced image gets one itemized warning.
	"""
	media_policy = media_assets.POLICY_REFERENCE_WARN

	#==============
	def __init__(self, package_name: str, verbose: bool = False) -> None:
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# Set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()

	#==============
	def read_package(self, infile: str) -> None:
		"""Read is not supported for this engine."""
		raise NotImplementedError

	#==============
	def _warn_about_item_media(self, item_bank: ItemBank) -> None:
		"""
		Print one itemized warning per image referenced by the item bank.

		Exam YAML carries images through verbatim inside the "statement"
		string but has no channel to transport image files, so every
		engine-referenced image routes through the declared media_policy
		(reference_warn) and surfaces via the single
		media_assets.apply_media_policy warning channel.
		"""
		collected_assets = item_bank.collect_assets()
		for item_crc16, item_assets in collected_assets.item_dependencies.items():
			decision = media_assets.apply_media_policy(
				self.media_policy, item_assets, self.name, item_crc16)
			for warning in decision.warnings:
				print(warning)

	#==============
	def save_package(self, item_bank: ItemBank, outfile: str = None) -> str | None:
		"""
		Write the item bank to an exam YAML file.

		Returns:
			str: Path to the written file, or None if no items.
		"""
		outfile = self.get_outfile_name('exam', 'yaml', outfile)
		# emit the itemized image warnings before rendering item text
		self._warn_about_item_media(item_bank)
		# Render each item as a question dict
		assessment_items_tree = self.process_item_bank(item_bank)
		if len(assessment_items_tree) == 0:
			return None
		# Build the top-level YAML structure
		today_str = datetime.date.today().isoformat()
		exam_data = {
			"title": self.package_name,
			"date": today_str,
			"sections": [
				{
					"heading": self.package_name,
					"questions": assessment_items_tree,
				}
			],
		}
		# Write YAML to file
		with open(outfile, "w") as f:
			# use default_flow_style=False for readable block-style YAML
			# allow_unicode=True to preserve HTML entities in text
			yaml.dump(
				exam_data, f,
				default_flow_style=False,
				allow_unicode=True,
				sort_keys=False,
			)
		if self.verbose is True:
			count = len(assessment_items_tree)
			print(f"Saved {count} assessment items to {outfile}")
		return outfile
