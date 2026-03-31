# Standard Library
import re
import inspect
from collections import defaultdict
from qti_package_maker.common.tabulate_compat import tabulate

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

class ItemBank:
	"""
	A centralized storage system for assessment items using a dictionary keyed by CRC codes.
	"""
	def __init__(self, allow_mixed: bool = False):
		"""Initialize an empty item bank."""
		# Boolean if mixed item types are allow in the same item bank
		self.allow_mixed = allow_mixed
		# Dictionary to store items keyed by item_crc
		self.items_dict_key_list = []
		self.items_dict = {}
		# item_types and their class definitions
		self.item_classes = self._discover_item_classes()
		# Track the first added item type
		self.first_item_type = None
		self.used_item_types_set = set()
		self.crc16_pattern = re.compile(r"\b([0-9a-f]{4})(?:_[0-9a-f]{4})*\b")
		self.item_type_pattern = re.compile(r"^[A-Z_]+$")

	#============================================
	def _discover_item_classes(self) -> dict:
		"""
		Dynamically find all assessment item classes in item_types.py.
		Returns:
			dict: Mapping of item type names to their corresponding classes.
		"""
		classes = {}
		for name, obj in inspect.getmembers(item_types, inspect.isclass):
			if issubclass(obj, item_types.BaseItem) and obj is not item_types.BaseItem:
				classes[name.upper()] = obj
		return classes

	#============================================
	def get_available_item_types(self) -> list:
		"""Returns a list of available assessment item types."""
		return list(self.item_classes.keys())

	#============================================
	def show_available_item_types(self) -> None:
		"""Prints the available assessment item types."""
		print("Available Assessment Item Types:")
		for item_type in self.get_available_item_types():
			print(f"- {item_type}")

	#============================================
	def summarize_item_types(self) -> None:
		"""
		Generates a formatted ASCII table summarizing the count of each item type.
		"""
		item_type_counts = defaultdict(int)
		# Count item types
		for item_cls in self.items_dict.values():
			item_type_counts[item_cls.item_type] += 1
		# Sort the dictionary by item_type
		sorted_items = sorted(item_type_counts.items(), key=lambda x: x[0])
		# Prepare data for tabulate
		data = [[item_type, count] for item_type, count in sorted_items]
		# Print the summary table using tabulate
		print("\nItem Bank Summary")
		print(tabulate(data, headers=["Item Type", "Count"], tablefmt="fancy_outline"))

	#============================================
	def gather_histogram_data(self, item_type: str) -> dict:
		"""
		Gathers histogram data for a given item type.
		"""
		answer_counts = defaultdict(int)
		for crc16_key in self.items_dict_key_list:
			item_cls = self.items_dict[crc16_key]
			if item_cls.item_type != item_type:
				continue
			if item_type == "MC":
				answer_counts[item_cls.answer_index] += 1
			elif item_type == "MA":
				for index in item_cls.answer_index_list:
					answer_counts[index] += 1
		# Return after processing all items
		return answer_counts

	#============================================
	def print_histogram(self) -> None:
		"""
		Summarizes the count of each item type in items_dict and prints histograms for supported types.
		"""
		if len(self.items_dict_key_list) == 0:
			return
		# Check if 'MC' type items exist and print their histogram
		if 'MC' in self.used_item_types_set:
			self.print_histogram_MC_items()
		# Check if 'MA' type items exist and print their histogram
		if 'MA' in self.used_item_types_set:
			self.print_histogram_MA_items()

	#============================================
	def print_histogram_MC_items(self) -> None:
		"""
		Prints a histogram summarizing the distribution of answers for Multiple Choice (MC) items.
		"""
		self.print_histogram_type("MC", "Multiple Choice (MC)")

	#============================================
	def print_histogram_MA_items(self) -> None:
		"""
		Prints a histogram summarizing the distribution of answers for Multiple Answer (MA) items.
		"""
		self.print_histogram_type("MA", "Multiple Answer (MA)")

	#============================================
	def print_histogram_type(self, item_type: str, title: str):
		"""
		Prints a formatted histogram for the given item type using tabulate.
		Args:
			item_type (str): The type of item to analyze.
			title (str): Title of the histogram.
		"""
		answer_counts = self.gather_histogram_data(item_type)
		if not answer_counts:
			print(f"No data available for {title} histogram.")
			return

		# Prepare data for tabulate
		data = []
		total_answers = sum(answer_counts.values())
		max_index = max(answer_counts.keys())
		for index in range(max_index + 1):
			letter = string_functions.number_to_letter(index + 1)
			count = answer_counts.get(index, 0)
			percent = 100 * count / float(total_answers) if total_answers > 0 else 0
			data.append([letter, count, f"{percent:.1f}%"])

		# Print histogram using tabulate
		print(f"\n{title} Histogram")
		print(tabulate(data, headers=["Letter", "Count", "%"], tablefmt="fancy_outline"))

	#============================================
	def _validate_item_type(self, item_type: str) -> None:
		"""
		Ensures consistency of item types if allow_mixed is False.
		"""
		if self.allow_mixed:
			return
		if self.first_item_type is None:
			# Set the first item type
			self.first_item_type = item_type
			return
		if self.first_item_type == item_type:
			return
		raise ValueError("Error: Mixing item types is not allowed. "
			+ f"allowed type is '{self.first_item_type}', attempted to add '{item_type}'")

	#============================================
	def add_item(self, item_type: str, item_tuple: tuple) -> None:
		"""
		Creates and adds an assessment item to the bank.
		Args:
			item_type (str): The type of assessment item.
			item_tuple (tuple): The parameters needed to create the item.
		"""
		item_type = item_type.upper()
		# Validate item_type format pattern (ALL CAPS + UNDERSCORES ONLY)
		if not self.item_type_pattern.fullmatch(item_type):
			self.show_available_item_types()
			raise ValueError(f"Invalid item_type format: '{item_type}'")
		if item_type not in self.item_classes:
			self.show_available_item_types()
			raise NotImplementedError(f"Error: Unsupported assessment item type '{item_type}'")
		self._validate_item_type(item_type)
		# Instantiate the assessment item
		item_cls = self.item_classes[item_type](*item_tuple)
		# Use add_item_cls to add it
		self.add_item_cls(item_cls)

	#============================================
	def add_item_cls(self, item_cls: item_types.BaseItem) -> None:
		"""
		Adds an existing item_cls instance to the bank.
		"""
		# Ensure item_cls is actually a BaseItem
		if not isinstance(item_cls, item_types.BaseItem):
			raise TypeError(f"Expected a BaseItem, got {type(item_cls).__name__}")
		# Assign an item number
		item_cls.item_number = len(self.items_dict) + 1
		self._validate_item_type(item_cls.item_type)
		# Validate CRC16 format (must be 4-character hex pairs separated by underscores)
		item_crc16 = item_cls.item_crc16
		if not self.crc16_pattern.fullmatch(item_crc16):
			raise ValueError(f"Invalid CRC16 format: '{item_crc16}'")
		# Prevent duplicates
		if item_crc16 in self.items_dict:
			#raise ValueError(f"Duplicate item with CRC16 '{item_crc16}' detected.")
			print(f"Warning: Duplicate item with CRC16 '{item_crc16}' detected.")
			print("skipping...")
			return
		# Store the item and track the key order
		self.items_dict[item_crc16] = item_cls
		self.items_dict_key_list.append(item_crc16)
		# Ensure dictionary and key list remain in sync
		if len(self.items_dict) != len(self.items_dict_key_list):
			raise ValueError("Mismatch between items_dict and items_dict_key_list after add_item_cls.")
		# Track used item types
		self.used_item_types_set.add(item_cls.item_type)

	#============================================
	def renumber_items(self) -> None:
		for number, item_cls in enumerate(self.items_dict.values(), start=1):
			item_cls.item_number = number
		return

	#============================================
	def merge(self, other: "ItemBank") -> "ItemBank":
		"""
		Merges two ItemBank objects, ensuring no duplicate items.
		Args:
			other (ItemBank): Another ItemBank to merge with.
		Returns:
			ItemBank: A new ItemBank containing the union of assessment items.
		"""
		# Ensure that the object being merged is an instance of ItemBank
		if not isinstance(other, ItemBank):
			raise TypeError("Can only merge with another ItemBank instance")
		# Determine the new allow_mixed value after merging
		merged_allow_mixed = self.allow_mixed or other.allow_mixed
		# Ensure mixed types are not allowed if allow_mixed is False
		if not merged_allow_mixed:
			if self.first_item_type is not None and other.first_item_type is not None:
				if self.first_item_type != other.first_item_type:
					raise ValueError("Error: Mixing item types is not allowed. "
						+ f"allowed type is '{self.first_item_type}', attempted to add '{other.first_item_type}'")
		# Create a new merged ItemBank with the determined allow_mixed setting
		merged_bank = ItemBank(allow_mixed=merged_allow_mixed)
		# Merge dictionaries, ensuring no duplicate items
		merged_bank.items_dict = {**self.items_dict, **other.items_dict}
		# Make a new list of keys
		new_items_dict_key_list = self.items_dict_key_list.copy()
		# Merge item keys while maintaining order and avoiding duplicates
		existing_keys = set(new_items_dict_key_list)
		for key in other.items_dict_key_list:
			if key not in existing_keys:
				new_items_dict_key_list.append(key)
				existing_keys.add(key)
		merged_bank.items_dict_key_list = new_items_dict_key_list
		# Ensure consistency: length of keys list should match items_dict
		if len(merged_bank.items_dict) != len(merged_bank.items_dict_key_list):
			raise ValueError("Mismatch between items_dict and items_dict_key_list after merge.")
		# Merge sets to track all used item types from both banks
		merged_bank.used_item_types_set = self.used_item_types_set | other.used_item_types_set
		# Preserve first item type when mixed types are not allowed
		if not merged_allow_mixed:
			merged_bank.first_item_type = self.first_item_type or other.first_item_type

		return merged_bank

	#============================================
	def union(self, other: "ItemBank") -> "ItemBank":
		"""Alias for merging two ItemBank"""
		return self.merge(other)

	#============================================
	def __or__(self, other: "ItemBank") -> "ItemBank":
		"""Alias for merging two ItemBank objects using the `|` operator."""
		return self.merge(other)

	#============================================
	def __add__(self, other: "ItemBank") -> "ItemBank":
		"""Alias for merging two ItemBank objects using the `+` operator."""
		return self.merge(other)

	#============================================
	def __len__(self) -> int:
		"""Returns the number of items in the ItemBank."""
		return len(self.items_dict)

	#============================================
	def __getitem__(self, index):
		"""
		Supports both direct indexing and slicing.
		- If given an integer, returns the single item.
		- If given a slice, returns a new ItemBank with a subset of items.
		"""
		if isinstance(index, slice):  # Handle slicing
			new_bank = ItemBank(self.allow_mixed)
			# Slice the ordered list
			for key in self.items_dict_key_list[index]:
				new_bank.add_item_cls(self.items_dict[key])
			# Returns a new trimmed ItemBank
			return new_bank
		elif isinstance(index, int):
			# Handle single index access
			key = self.items_dict_key_list[index]
			# Returns the full item
			return self.items_dict[key]
		else:
			raise TypeError(f"Invalid index type: {type(index)}. Expected int or slice.")

	#============================================
	def __setitem__(self, index, item_cls):
		"""
		Allows modifying the location of a key in the list order.
		Only moves an existing item by its key.
		"""
		if not (0 <= index < len(self.items_dict_key_list)):
			raise IndexError(f"Index {index} is out of bounds for item bank.")
		if not isinstance(item_cls, item_types.BaseItem):
			raise TypeError(f"Expected a Item instance, got {type(item_cls).__name__}")
		key = item_cls.item_crc16
		if key not in self.items_dict:
			# Situation 1: New Item -> Add at the specified index
			self.items_dict[key] = item_cls
			# Insert at requested index
			self.items_dict_key_list.insert(index, key)
		else:
			# Situation 2: Existing Item -> Move it to the new position
			self.items_dict_key_list.remove(key)
			# Insert at requested index
			self.items_dict_key_list.insert(index, key)

	#============================================
	def __repr__(self) -> str:
		"""
		Returns a concise string representation for debugging.
		Shows the number of items and the ordered list of keys.
		"""
		return f"<ItemBank: {len(self.items_dict)} items, keys={self.items_dict_key_list}>"

	#============================================
	def sort(self) -> None:
		"""
		Sorts the items in the bank based on their item_crc16 values.
		"""
		self.items_dict_key_list.sort()

	#============================================
	def __eq__(self, other: object) -> bool:
		"""
		Checks if two ItemBank instances are equal.
		Two banks are equal if:
		1. They have the same number of items (fast check)
		2. They contain the same items (same keys)
			- The key itself is a hash of the value,
			  so checking only keys is sufficient.
		3. Two lists are the same if they have the same keys
			- even if the keys are in a different order
		"""
		# Can't compare to non-ItemBank objects
		if not isinstance(other, ItemBank):
			return False
		# Check the lengths first because it is faster than set comparison
		if len(self.items_dict) != len(other.items_dict):
			return False
		# Order-independent comparison
		return set(self.items_dict.keys()) == set(other.items_dict.keys())

	#============================================
	def __iter__(self):
		"""Allows iteration over the items in insertion order."""
		for key in self.items_dict_key_list:
			# Yield the full item object
			yield self.items_dict[key]

def main():
	#==========================
	# Basic Functionality Tests
	#==========================
	bank1 = ItemBank()
	bank1.add_item("MC", ("Question 1", ["A", "B", "C"], "A"))
	bank1.add_item("MC", ("Question 2", ["X", "Y", "Z"], "Y"))
	print(f"bank1: {bank1}")

	bank2 = ItemBank()
	bank2.add_item("MC", ("Question 3", ["1", "2", "3"], "3"))
	bank2.add_item("MC", ("Question 4", ["2", "3", "4"], "3"))
	bank2.add_item("MC", ("Question 5", ["3", "4", "5"], "3"))
	print(f"bank2: {bank2}")

	# Merge banks
	merged_bank = bank1.merge(bank2)
	print(f"merged_bank: {merged_bank}")
	assert len(merged_bank) == len(bank1) + len(bank2)
	# test operators
	assert merged_bank == bank1 + bank2
	assert merged_bank == bank1 | bank2
	assert bank2.merge(bank1) == bank1.merge(bank2)

	# Shuffle and sort
	import random
	random.shuffle(merged_bank)
	print(f"shuffle: {merged_bank}")
	for item_cls in merged_bank:
		print(item_cls)

	sorted_item_list = sorted(merged_bank)
	sorted_bank = ItemBank()
	for item_cls in sorted_item_list:
		# Re-add items in order
		sorted_bank.add_item_cls(item_cls)
	print(f"sorted: {sorted_bank}")
	assert sorted_bank == merged_bank

	# Sorting when already sorted (should remain the same)
	sorted_bank.sort()
	print(f"sorted_again: {sorted_bank}")
	assert sorted_bank == merged_bank

	#==========================
	# Duplicate Items
	#==========================

	bank1 = ItemBank()
	bank1.add_item("MC", ("Question 1", ["A", "B", "C"], "A"))
	bank1.add_item("MC", ("Question 2", ["X", "Y", "Z"], "Y"))
	print(f"bank1: {bank1}")
	bank2 = ItemBank()
	bank2.add_item("MC", ("Question 2", ["X", "Y", "Z"], "Y"))
	bank2.add_item("MC", ("Question 3", ["1", "2", "3"], "3"))
	bank2.add_item("MC", ("Question 3b", ["1", "2", "3"], "3"))
	print(f"bank2: {bank2}")
	# Merge banks
	merged_bank = bank1.merge(bank2)
	print(f"merged_bank: {merged_bank}")
	assert len(merged_bank) == len(bank1) + len(bank2) - 1
	merged_bank.print_histogram()

	#==========================
	# Edge Cases & Error Handling
	#==========================

	# Test empty bank behavior
	empty_bank = ItemBank()
	print(f"empty_bank: {empty_bank}")
	# Should be empty
	assert len(empty_bank) == 0

	# Merging an empty bank
	merged_with_empty = merged_bank.merge(empty_bank)
	print(f"merged_with_empty: {merged_with_empty}")
	# Should be unchanged
	assert merged_with_empty == merged_bank

	# Preventing duplicate items (should not add duplicate)
	duplicate_bank = ItemBank()
	duplicate_bank.add_item("MC", ("Question 1", ["A", "B", "C"], "A"))
	merged_duplicate = bank1.merge(duplicate_bank)
	print(f"merged_duplicate: {merged_duplicate}")  # Should not change
	assert bank1 == merged_duplicate

	# Moving an item to a different index
	print(f"Before reordering: {merged_bank}")
	merged_bank[0], merged_bank[2] = merged_bank[2], merged_bank[0]  # Swap first and last
	print(f"After reordering: {merged_bank}")

	# Test item replacement
	item_cls = merged_bank[1]  # Get key of the second item
	merged_bank[1] = item_cls  # Should not change anything
	print(f"After item replacement: {merged_bank}")

	#==========================
	# Error Handling Tests
	#==========================

	# Attempting to merge different item types with allow_mixed=True
	mixed_bank = ItemBank(allow_mixed=True)
	mixed_bank.add_item("NUM", ("Pi Approximation?", 3.14, 0.01))
	bank1.merge(mixed_bank)
	mixed_bank = mixed_bank.merge(bank1)
	mixed_bank.summarize_item_types()

	try:
		# Attempting to merge different item types without allow_mixed=True
		mixed_bank = ItemBank()
		mixed_bank.add_item("NUM", ("Pi Approximation?", 3.14, 0.01))
		bank1.merge(mixed_bank)  # Should raise ValueError
	except ValueError as e:
		print(f"Expected Error: {e}")

	try:
		# Trying to add an unsupported item type
		bank1.add_item("INVALID", ("Bad Question", ["X", "Y"], "X"))
	except NotImplementedError as e:
		print(f"Expected Error: {e}")

	try:
		# Trying to move a non-existent key
		merged_bank[0] = None
	except TypeError as e:
		print(f"Expected Error: {e}")





if __name__ == "__main__":
	main()
