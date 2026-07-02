ENGINE_NAME = "human_readable"

# Standard Library
import re

# QTI Package Maker
from qti_package_maker.common import string_functions
from qti_package_maker.common import media_assets
from qti_package_maker.assessment_items import item_types

#==============================================================
def is_valid_content(content_text: str) -> bool:
	if '<mathml' in content_text.lower():
		#print("problem contains mathml")
		return False
	if 'rdkit' in content_text.lower():
		#print("problem contains rdkit")
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
	"""Render an MC item in the human-readable format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	if not is_valid_list(item_cls.choices_list):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	assessment_text += '\n'
	already_has_prefix = string_functions.has_prefix(item_cls.choices_list)
	for i, choice_text in enumerate(item_cls.choices_list):
		if choice_text == item_cls.answer_text:
			prefix = '*'
		else:
			prefix = ' '
		pretty_choice = string_functions.make_question_pretty(choice_text)
		if already_has_prefix:
			assessment_text += f"- [{prefix}] {pretty_choice}\n"
		else:
			letter_prefix = string_functions.number_to_letter(i+1)
			assessment_text += f"- [{prefix}] {letter_prefix}. {pretty_choice}\n"
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
def MA(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str, question_text: str, choices_list: list, answers_list: list):
	"""Render an MA item in the human-readable format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	if not is_valid_list(item_cls.choices_list):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	assessment_text += '\n'
	already_has_prefix = string_functions.has_prefix(item_cls.choices_list)
	for i, choice_text in enumerate(item_cls.choices_list):
		if choice_text in item_cls.answers_list:
			prefix = '*'
		else:
			prefix = ' '
		pretty_choice = string_functions.make_question_pretty(choice_text)
		if already_has_prefix:
			assessment_text += f"- [{prefix}] {pretty_choice}\n"
		else:
			letter_prefix = string_functions.number_to_letter(i+1)
			assessment_text += f"- [{prefix}] {letter_prefix}. {pretty_choice}\n"
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
def MATCH(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""Render a MATCH item in the human-readable format."""
	#MAT TAB question text TAB answer text TAB matching text TAB answer two text TAB matching two text
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	if not is_valid_list(item_cls.prompts_list):
		return None
	if not is_valid_list(item_cls.choices_list):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	assessment_text += '\n'
	already_has_prefix = string_functions.has_prefix(item_cls.prompts_list) or string_functions.has_prefix(item_cls.choices_list)
	num_items = min(len(item_cls.prompts_list), len(item_cls.choices_list))
	max_prompt_length = max(len(string_functions.make_question_pretty(text)) for text in item_cls.prompts_list)
	#print(f"max_prompt_length = {max_prompt_length}")
	#max_choice_length = max(len(text) for text in item_cls.choices_list)
	for i in range(num_items):
		prompt_text = string_functions.make_question_pretty(item_cls.prompts_list[i])
		choice_text = string_functions.make_question_pretty(item_cls.choices_list[i])
		if already_has_prefix:
			assessment_text += f"- {prompt_text.rjust(max_prompt_length)} / {choice_text}\n"
		else:
			letter_prefix = string_functions.number_to_letter(i+1)
			assessment_text += f"- {i+1}. {prompt_text.rjust(max_prompt_length)} / {letter_prefix}. {choice_text}\n"
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
def NUM(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str,
	#question_text: str, answer_float: float, tolerance_float: float, tolerance_message=True):
	"""Render a NUM item in the human-readable format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	if item_cls.tolerance_message:
		assessment_text += f"\n(Note: Answer must be within &pm;{item_cls.tolerance_float} of the correct value)"
	assessment_text += '\n'
	assessment_text += f"- Answer: [____] (Correct: {item_cls.answer_float:.3f})"  # Display correct answer
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
def FIB(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str, question_text: str, answers_list: list):
	"""Render a FIB item in the human-readable format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	if not is_valid_list(item_cls.answers_list):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	assessment_text = assessment_text.replace("____", "[____]")  # Ensure consistent blank formatting
	assessment_text += '\n'
	for i, answer_text in enumerate(item_cls.answers_list):
		letter_prefix = string_functions.number_to_lowercase(i+1)
		pretty_answer_text = string_functions.make_question_pretty(answer_text)
		assessment_text += f"- Answer: [{letter_prefix}] {pretty_answer_text}\n"
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
# Create a Fill-in-the-Blank (Multiple Blanks) question using answer mapping.
def MULTI_FIB(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""Render a MULTI_FIB item in the human-readable format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	assessment_text += '\n'
	for i, fib_variable_name in enumerate(item_cls.answer_map.keys()):
		assessment_text += f"Blank {i+1}. {fib_variable_name}:\n"
		answers_list = item_cls.answer_map[fib_variable_name]
		for j, answer_text in enumerate(answers_list):
			letter_prefix = string_functions.number_to_lowercase(j+1)
			pretty_answer_text = string_functions.make_question_pretty(answer_text)
			# Show correct answers per blank
			assessment_text += f"- [{letter_prefix}] {pretty_answer_text}\n"
		assessment_text += '\n'
	assessment_text += '\n'
	return assessment_text

#==============================================================
def ORDER(item_cls: item_types.BaseItem) -> str | None:
	#item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	"""Render an ORDER item in the human-readable format."""
	local_question_text = string_functions.make_question_pretty(item_cls.question_text)
	if not is_valid_content(local_question_text):
		return None
	if not is_valid_list(item_cls.ordered_answers_list):
		return None
	assessment_text = ''
	assessment_text += local_question_text
	assessment_text += '\n'
	for i, answer_text in enumerate(item_cls.ordered_answers_list):
		# Display correct answer next to blank
		assessment_text += f"- [{i+1}] [____] (Correct: {answer_text})\n"
	assessment_text += '\n\n'
	return assessment_text

#==============================================================
# whole <img ...> tag / src="..." patterns come from media_assets (single owner);
# only the alt attribute pattern is local to this engine
_ALT_ATTR_PATTERN = re.compile(r"""\balt\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)

def _describe_image(asset: media_assets.MediaAsset, alt_text: str) -> str:
	"""
	Build a readable inline description of an image reference: name, alt
	text, and source path. human_readable never copies or embeds files.
	"""
	description = media_assets.placeholder_text(asset)
	if alt_text:
		description += f" (alt: {alt_text})"
	description += f" (source: {asset.src})"
	return description

#==============================================================
def _replace_img_tags_in_text(text: str, asset_by_src: dict) -> str:
	"""Replace every <img src=...> tag in one string field with its description."""
	#----------------------------------------------------
	def _substitute(tag_match: re.Match) -> str:
		tag = tag_match.group(0)
		src_match = media_assets.SRC_ATTR_PATTERN.search(tag)
		if src_match is None:
			return tag
		src = src_match.group(3)
		asset = asset_by_src.get(src)
		if asset is None:
			return tag
		alt_match = _ALT_ATTR_PATTERN.search(tag)
		alt_text = alt_match.group(2) if alt_match else ""
		return _describe_image(asset, alt_text)

	return media_assets.IMG_TAG_PATTERN.sub(_substitute, text)

#==============================================================
def _replace_img_tags_in_value(value: object, asset_by_src: dict) -> object:
	"""Recurse into a supporting-field value (str, list, or dict) and replace <img> tags."""
	if isinstance(value, str):
		return _replace_img_tags_in_text(value, asset_by_src)
	if isinstance(value, list):
		return [_replace_img_tags_in_value(element, asset_by_src) for element in value]
	if isinstance(value, dict):
		return {key: _replace_img_tags_in_value(element, asset_by_src) for key, element in value.items()}
	return value

#==============================================================
def clone_item_with_image_descriptions(
			item_cls: item_types.BaseItem, asset_by_src: dict) -> item_types.BaseItem:
	"""
	Return a deep copy of item_cls with every <img> tag in its HTML-bearing
	fields replaced by a readable name + alt + source-path description.

	This must run BEFORE rendering (not on the rendered text afterward)
	because make_question_pretty strips every HTML tag it does not
	specifically recognize, including <img>, from the final output.
	"""
	cloned_item = item_cls.copy()
	cloned_item.question_text = _replace_img_tags_in_text(item_cls.question_text, asset_by_src)
	for field_name in item_cls.get_supporting_field_names():
		field_value = getattr(item_cls, field_name)
		setattr(cloned_item, field_name, _replace_img_tags_in_value(field_value, asset_by_src))
	return cloned_item
