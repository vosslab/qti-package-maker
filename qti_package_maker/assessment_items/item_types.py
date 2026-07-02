
# Standard Library
import re
import time
import copy

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import validator

#============================================
# TODO: Future Enhancements for Assessment Items
#============================================
#
# 1. **Feedback for Correct/Incorrect Responses**
#    - Add `self.feedback_correct` and `self.feedback_incorrect` attributes.
#    - Ensure `get_tuple()` includes feedback data.
#
# 2. **Shuffle Choices Boolean for MC/MA Questions**
#    - Introduce `self.shuffle_choices = False` to allow randomized choices.
#    - Ensure answer order randomization is handled when exporting.
#
# 3. **Hints for Students**
#    - Add `self.hint` to provide optional hints before answering.
#    - Ensure `get_tuple()` includes hint data.
#
#============================================

class BaseItem:
	"""
	Base class for all assessment items.
	Handles validation, CRC calculations, and common properties.
	"""
	def __init__(self, question_text: str) -> None:
		"""
		Initializes a base assessment item.
		Ensures necessary properties are set and validates the item.
		"""
		# Ensure that secondary_crc16 is set in subclasses before proceeding
		if not hasattr(self, 'secondary_crc16'):
			raise AttributeError(
				f"{self.__class__.__name__} must define 'secondary_crc16' before calling BaseItem.__init__()"
			)
		self.crc16_pattern = re.compile(r"\b([0-9a-f]{4})(?:_[0-9a-f]{4})*\b")
		self.item_type_pattern = re.compile(r"^[A-Z_]+$")
		# feedback
		self.feedback_correct = None
		self.feedback_incorrect = None
		# Store the time of item creation
		self.timestamp = time.time()
		self.item_number = 0
		# Store the question text
		self.question_text = string_functions.strip_crc_prefix(question_text)
		# Compute CRC16 hash for the question text
		self.question_crc16 = string_functions.get_crc16_from_string(self.question_text)
		# Combine question CRC16 with options CRC16 to create a unique item CRC
		self.item_crc16 = f"{self.question_crc16}_{self.secondary_crc16}"
		if not self.crc16_pattern.fullmatch(self.item_crc16):
			raise ValueError(f"Invalid CRC16 format: '{self.item_crc16}'")
		# Validate the item using the appropriate validation function
		self._validate()

	#============================================
	def __lt__(self, other: "BaseItem") -> bool:
		"""Defines sorting based on item_crc16."""
		# Sort by CRC
		return self.item_crc16 < other.item_crc16

	#============================================
	def __eq__(self, other: object) -> bool:
		if not isinstance(other, BaseItem):
			return False
		# Compare by CRC16
		return self.item_crc16 == other.item_crc16

	#============================================
	def __repr__(self) -> str:
		"""
		Returns a compact yet informative string representation of the item.
		Includes item type, CRC, and question preview.
		"""
		preview_text = self.question_text[:30] + "..." if len(self.question_text) > 30 else self.question_text
		return f"<Item: {self.item_type}: {self.item_crc16}, '{preview_text}'>"

	#============================================
	def copy(self) -> "BaseItem":
		"""
		Creates a deep copy of the assessment item.
		- Ensures that modifying the copy does not affect the original.
		- Works for all subclasses without modification.
		Returns:
				BaseItem: A new independent copy of the object.
		"""
		return copy.deepcopy(self)

	#==============
	@property
	def item_type(self) -> str:
		"""
		Dynamically retrieves the class name as the item type.
		Used to determine validation and processing logic.
		"""
		# Return the name of the subclass (e.g., 'MC', 'MA', etc.)
		return self.__class__.__name__

	#==============
	def _validate(self) -> None:
		"""
		Calls the appropriate validator function for the item type.
		Ensures the item meets required structure and content constraints.
		"""
		# Retrieve the validation function dynamically based on item type
		validate_function = getattr(validator, f"validate_{self.item_type}")
		# Call the validation function with question text and item-specific parameters
		validate_function(self.question_text, *self.get_tuple())

	#==============
	def get_supporting_field_names(self) -> tuple:
		"""
		Returns a list of attribute names that are part of the supporting elements
		of the assessment item (everything that is NOT the question_text).
		"""
		raise NotImplementedError("Subclasses must implement get_supporting_field_names().")

	#==============
	def get_tuple(self) -> tuple:
		"""
		Dynamically constructs and returns a tuple of supporting fields.
		"""
		supporting_field_data = []
		for field_name in self.get_supporting_field_names():
			data = getattr(self, field_name)
			if data is None or data == "":
				raise ValueError(f"Invalid empty value detected in {self.item_type}, {self}")
			supporting_field_data.append(data)
		return tuple(supporting_field_data)

#============================================
#============================================
#============================================
#============================================
class MC(BaseItem):
	def __init__(self, question_text: str, choices_list: list, answer_text: str) -> None:
		self.choices_list = string_functions.remove_prefix_from_list(choices_list)
		self.answer_text = string_functions.strip_prefix_from_string(answer_text)
		secondary_string = "|".join(choices_list)
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		self.answer_index = choices_list.index(answer_text)
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("choices_list", "answer_text")

#============================================
class MA(BaseItem):
	def __init__(
		self,
		question_text: str,
		choices_list: list,
		answers_list: list,
		min_answers_required: int = 1,
		allow_all_correct: bool = True,
	) -> None:
		self.choices_list = string_functions.remove_prefix_from_list(choices_list)
		self.answers_list = string_functions.remove_prefix_from_list(answers_list)
		self.min_answers_required = min_answers_required
		self.allow_all_correct = allow_all_correct
		secondary_string = "|".join(choices_list)
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		self.answer_index_list = [choices_list.index(answer_text) for answer_text in answers_list]
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("choices_list", "answers_list", "min_answers_required", "allow_all_correct")

#============================================
class MATCH(BaseItem):
	def __init__(self, question_text: str, prompts_list: list, choices_list: list) -> None:
		self.prompts_list = string_functions.remove_prefix_from_list(prompts_list)
		self.choices_list = string_functions.remove_prefix_from_list(choices_list)
		secondary_string = "|".join(prompts_list+choices_list)
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("prompts_list", "choices_list")

#============================================
class NUM(BaseItem):
	def __init__(self, question_text: str, answer_float: float, tolerance_float: float, tolerance_message: bool = True) -> None:
		self.answer_float = answer_float
		self.tolerance_float = tolerance_float
		self.tolerance_message = tolerance_message
		secondary_string = f"{answer_float:.2e}_{tolerance_float:.2e}"
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("answer_float", "tolerance_float", "tolerance_message")

#============================================
class FIB(BaseItem):
	def __init__(self, question_text: str, answers_list: list) -> None:
		self.answers_list = string_functions.remove_prefix_from_list(answers_list)
		secondary_string = "|".join(answers_list)
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("answers_list",)

#============================================
class MULTI_FIB(BaseItem):
	def __init__(self, question_text: str, answer_map: dict) -> None:
		self.answer_map = answer_map
		secondary_string = '|'.join(f"{k}:{v}" for k, v in sorted(answer_map.items()))
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("answer_map",)

#============================================
class ORDER(BaseItem):
	def __init__(self, question_text: str, ordered_answers_list: list) -> None:
		self.ordered_answers_list = string_functions.remove_prefix_from_list(ordered_answers_list)
		secondary_string = "|".join(ordered_answers_list)
		self.secondary_crc16 = string_functions.get_crc16_from_string(secondary_string)
		super().__init__(question_text)
	#================
	def get_supporting_field_names(self) -> tuple:
		return ("ordered_answers_list",)
