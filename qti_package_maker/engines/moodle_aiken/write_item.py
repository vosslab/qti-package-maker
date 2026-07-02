ENGINE_NAME = "moodle_aiken"

# Standard Library
import re

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

"""
Render assessment items into the Moodle Aiken text format
(https://docs.moodle.org/en/Aiken_format). Aiken is strict plain text with no
markup channel for images, so EngineClass.save_package (media_policy
placeholder_warn) replaces every <img> tag with a readable
`[image: name.ext]` placeholder plus an itemized warning before writing.
"""

#==============================================================
def is_valid_content(content_text: str) -> bool:
	#override for now
	return True

	if '<mathml' in content_text.lower():
		#print("problem contains mathml")
		return False
	if 'rdkit' in content_text.lower():
		#print("problem contains rdkit")
		return False
	if '<table' in content_text.lower():
		#print("problem contains a table")
		return False
	return True

#====================
def is_valid_list(list_of_strings: list) -> bool:
	for content_text in list_of_strings:
		if not is_valid_content(content_text):
			return False
	return True

#==============================================================
def MC(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str, question_text: str, choices_list: list, answer_text: str):
	"""Render an MC item in Moodle Aiken format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	if not is_valid_list(item_cls.choices_list):
		return None
	assessment_text = ''
	assessment_text += item_cls.question_text
	assessment_text += '\n'
	already_has_prefix = string_functions.has_prefix(item_cls.choices_list)
	for i, choice_text in enumerate(item_cls.choices_list):
		local_choice_text = choice_text
		if already_has_prefix:
			local_choice_text = string_functions.strip_prefix_from_string(local_choice_text)
		letter_prefix = string_functions.number_to_letter(i+1)
		assessment_text += f"{letter_prefix}. {local_choice_text}\n"
	answer_letter = string_functions.number_to_letter(item_cls.answer_index+1)
	assessment_text += f"ANSWER: {answer_letter}\n"
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
def MA(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, choices_list: list, answers_list: list):
	"""Moodle Aiken writer does not implement MA items."""
	return None

#==============================================================
def MATCH(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""Moodle Aiken writer does not implement MATCH items."""
	#MAT TAB question text TAB answer text TAB matching text TAB answer two text TAB matching two text
	return None

#==============================================================
def NUM(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str,
	#question_text: str, answer_float: float, tolerance_float: float, tolerance_message=True):
	"""Moodle Aiken writer does not implement NUM items."""
	return None

#==============================================================
def FIB(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, answers_list: list):
	"""Moodle Aiken writer does not implement FIB items."""
	return None

#==============================================================
# Create a Fill-in-the-Blank (Multiple Blanks) question using answer mapping.
def MULTI_FIB(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""Moodle Aiken writer does not implement MULTI_FIB items."""
	return None

#==============================================================
def ORDER(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	"""Moodle Aiken writer does not implement ORDER items."""
	return None

#==============================================================
# whole <img ...> tag / src="..." patterns come from media_assets (single owner)

def replace_images_with_placeholders(text: str, placeholders_by_src: dict) -> str:
	"""
	Replace every <img src=...> tag in rendered writer output with its
	`[image: name.ext]` placeholder text (media_assets.placeholder_text via
	apply_media_policy's placeholder_warn decision).
	"""
	#----------------------------------------------------
	def _substitute(tag_match: re.Match) -> str:
		tag = tag_match.group(0)
		src_match = media_assets.SRC_ATTR_PATTERN.search(tag)
		if src_match is None:
			return tag
		src = src_match.group(3)
		return placeholders_by_src.get(src, tag)

	return media_assets.IMG_TAG_PATTERN.sub(_substitute, text)
