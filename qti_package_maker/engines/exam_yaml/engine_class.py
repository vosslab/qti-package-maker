
# Standard Library
import datetime

# Pip3 Library
import yaml

# QTI Package Maker
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.exam_yaml import write_item

class EngineClass(base_engine.BaseEngine):
	"""
	Write-only engine that exports an ItemBank to exam YAML format.

	Exam YAML is a print-oriented format for generating ODT exams.
	It is intentionally lossy: answer keys, scoring metadata, and
	section structure are not preserved.
	"""
	#==============
	def __init__(self, package_name: str, verbose: bool = False):
		# Call the base engine constructor
		super().__init__(package_name, verbose)
		# Set the write_item module (required)
		self.write_item = write_item
		# Verify that the correct write_item module is imported
		self.validate_write_item_module()

	#==============
	def read_package(self, infile: str):
		"""Read is not supported for this engine."""
		raise NotImplementedError

	#==============
	def save_package(self, item_bank, outfile: str = None) -> str:
		"""
		Write the item bank to an exam YAML file.

		Returns:
			str: Path to the written file, or None if no items.
		"""
		outfile = self.get_outfile_name('exam', 'yaml', outfile)
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
