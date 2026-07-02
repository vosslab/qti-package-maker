# Standard Library
import inspect
import re
import random

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines import base_engine
from qti_package_maker.engines import engine_registration

class QTIPackageInterface:
	#=====================================================================
	def __init__(self, package_name: str, verbose: bool = False, allow_mixed: bool = False) -> None:
		self.package_name = package_name.strip()
		self.verbose = verbose
		self.allow_mixed = allow_mixed
		self.item_bank = item_bank.ItemBank(self.allow_mixed)
		if not package_name:
			raise ValueError("package_name not defined")
		self._set_engine_data()

	#=====================================================================
	def _set_engine_data(self) -> None:
		"""Loads engine data from ENGINE_REGISTRY into self.engine_data."""
		if hasattr(self, "engine_data"):
			raise AttributeError("engine_data already exists")
		self.engine_data = {}  # Reset engine data dictionary
		for engine_name, engine_info in engine_registration.ENGINE_REGISTRY.items():
			self.engine_data[engine_name] = {
				"name": engine_info["engine_name"],
				"can_read": engine_info["can_read"],
				"can_write": engine_info["can_write"],
				"class": engine_info["engine_class"]
			}

	#=====================================================================
	def init_engine(self, input_engine_name: str) -> base_engine.BaseEngine:
		"""Retrieve the engine class based on the given engine name."""
		input_engine_name_low = re.sub(r"[^a-z0-9]", "", input_engine_name.lower())
		if not input_engine_name_low:
			raise ValueError("Unknown engine: empty input")
		# Use preloaded engine data
		matches = []
		exact_matches = []
		for engine_info in self.engine_data.values():
			engine_name = re.sub(r"[^a-z0-9]", "", engine_info["name"].lower())
			if engine_name == input_engine_name_low:
				exact_matches.append(engine_info)
			if engine_name.startswith(input_engine_name_low):
				matches.append(engine_info)
		if len(exact_matches) == 1:
			engine_info = exact_matches[0]
		elif len(exact_matches) > 1:
			candidates = ", ".join(sorted([info["name"] for info in exact_matches]))
			raise ValueError(f"Ambiguous engine name '{input_engine_name}'. Candidates: {candidates}")
		elif len(matches) == 1:
			engine_info = matches[0]
		elif len(matches) > 1:
			candidates = ", ".join(sorted([info["name"] for info in matches]))
			raise ValueError(f"Ambiguous engine prefix '{input_engine_name}'. Candidates: {candidates}")
		else:
			self.show_available_engines()
			raise ValueError(f"Unknown engine: {input_engine_name}")
		engine_cls = engine_info["class"](self.package_name, self.verbose)
		if self.verbose:
			print(f"Initialized Engine: {engine_cls.name} ({engine_info['name']})")
		return engine_cls

	#=====================================================================
	def show_available_engines(self, tablefmt: str = "fancy_outline") -> None:
		"""
		Print all registered engines and their capabilities in a formatted tabulate table.
		"""
		engine_registration.print_engine_table(tablefmt)

	#=====================================================================
	def get_available_engines(self) -> list:
		return list(self.engine_data.keys())

	#=====================================================================
	def show_available_item_types(self) -> None:
		"""
		Print all registered engines and their capabilities in a formatted tabulate table.
		"""
		self.item_bank.show_available_item_types()

	#=====================================================================
	def reset_item_bank(self) -> None:
		# mostly for testing
		del self.item_bank
		self.item_bank = item_bank.ItemBank(self.allow_mixed)

	#=====================================================================
	def trim_item_bank(self, item_limit: int) -> None:
		if not item_limit:
			return
		if not isinstance(item_limit, int):
			raise ValueError
		if len(self.item_bank) <= item_limit:
			return
		# Randomly shuffle questions to ensure variety in selection
		random.shuffle(self.item_bank)
		# Limit the number of questions processed
		# Directly slice the ItemBank, thanks to __getitem__()
		self.item_bank = self.item_bank[:item_limit]
		return

	#=====================================================================
	def summarize_item_bank(self) -> None:
		"""Print all registered engines and their capabilities."""
		self.item_bank.summarize_items()

	#=====================================================================
	def print_item_bank_histogram(self) -> None:
		"""Print all registered engines and their capabilities."""
		self.item_bank.print_histogram()

	#=====================================================================
	def get_available_item_types(self) -> list:
		return self.item_bank.get_available_item_types()

	#=====================================================================
	def add_item(self, item_type: str, item_tuple: tuple) -> None:
		self.item_bank.add_item(item_type, item_tuple)

	#=====================================================================
	def read_package(self, input_file: str, engine_name: str) -> None:
		"""
		Reads an assessment package from the given input file and loads items into the item bank.
		"""
		engine_cls = self.init_engine(engine_name)

		# Ensure the selected engine supports reading
		if not hasattr(engine_cls, "read_items_from_file"):
			raise NotImplementedError(f"Engine {engine_cls.__class__.__name__} does not support reading.")

		# Retrieve the assessment items from the input file
		read_items_from_file = getattr(engine_cls, "read_items_from_file", None)
		if not callable(read_items_from_file):
			raise NotImplementedError(f"Engine {engine_cls.__class__.__name__} does not support reading.")

		sig = inspect.signature(read_items_from_file)
		if "allow_mixed" in sig.parameters:
			new_item_bank = read_items_from_file(input_file, allow_mixed=self.allow_mixed)
		else:
			new_item_bank = read_items_from_file(input_file)

		# If no items were read, notify the user and return
		if not new_item_bank or len(new_item_bank) == 0:
			print(f"Warning: No assessment items were found in the file: {input_file}.")
			return

		# Merge the newly read items into the existing item bank, avoiding duplicates
		self.item_bank += new_item_bank

		# Provide detailed output if verbosity is enabled
		if self.verbose:
			print(
				f"Successfully loaded {len(new_item_bank)} new assessment items from {input_file}.\n"
				f"The item bank now contains a total of {len(self.item_bank)} unique assessment items."
			)

	#=====================================================================
	def save_package(self, engine_name: str, outfile: str = None) -> str | None:
		"""
		Saves the current item bank using the specified engine.
		"""
		if len(self.item_bank) == 0:
			print("No assessment items to write, skipping save_package()")
			return
		self.item_bank.renumber_items()

		engine_cls = self.init_engine(engine_name)  # Initialize the engine
		if not hasattr(engine_cls, "save_package"):
			raise NotImplementedError(f"Engine {engine_cls.name} does not support writing.")

		if self.verbose:
			print(
				f"Saving package {engine_cls.name}\n"
				f"  with {len(self.item_bank)} assessment items."
			)
		outfile = engine_cls.save_package(self.item_bank, outfile)
		return outfile


#============================================
# If this script is run directly
#============================================
def main() -> None:

	# Parse arguments from the command line
	#args = parse_arguments()
	qti_packer = QTIPackageInterface('test_qti_maker', verbose=True, allow_mixed=True)
	qti_packer.show_available_engines()

	question_text = 'What is your favorite color?'
	answer_text = 'blue'
	choices_list = ['blue', 'red', 'yellow']
	qti_packer.add_item("MC", (question_text, choices_list, answer_text))

	question_text = 'Which are types of fruit?'
	answers_list = ['orange', 'banana', 'apple']
	choices_list = ['orange', 'banana', 'apple', 'lettuce', 'spinach']
	qti_packer.add_item("MA", (question_text, choices_list, answers_list))

	import time
	for engine_name in qti_packer.get_available_engines():
		print(f"\n\n... {engine_name} ...")
		qti_packer.save_package(engine_name)
		time.sleep(1)

if __name__ == "__main__":
	main()
