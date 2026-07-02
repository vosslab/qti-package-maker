ENGINE_NAME="bbq_text_upload"

# Standard Library
import re
import math
import random

# Pip3 Library (if applicable, add specific imports here)

# QTI Package Maker (if applicable, add specific imports here)
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

shuffle = False
letters = 'ABCDEFGHJKMNPQRSTUWXYZ'

"""
Render assessment items into Blackboard "BBQ" text upload format.
Refer to the Blackboard upload format documentation for field layout and rules.

Any <img> tag inside item HTML is carried through verbatim (clean_text_for_bbq
only normalizes whitespace); BBQ text upload has no channel to carry image
files, so EngineClass.save_package emits one itemized warning per referenced
image via qti_package_maker.common.media_assets.apply_media_policy.
"""

#==============================================================
def insert_prefix_inside_div(html: str, prefix: str) -> str:
	"""
	Insert the given prefix text immediately after the first <div ...> tag.
	"""
	return re.sub(r'(<div[^>]*>)', r'\1' + f'{prefix}. ', html, count=1)

#==============================================================
def clean_text_for_bbq(text: str) -> str:
	# Remove newlines
	text = text.replace('\n', ' ')
	# Remove tabs
	text = text.replace('\t', ' ')
	# Remove double spaces
	text = re.sub(r'\s+', ' ', text)
	return text.strip()

#==============================================================
# Create a Multiple Choice (Single Answer; Radio Buttons) question.
def MC(item_cls: item_types.MC) -> str:
	#item_number: int, item_cls.item_crc16: str, item_cls.question_text: str, item_cls.choices_list: list, answer_text: str) -> str:
	"""Render an MC item in BBQ text upload format."""
	# Initialize the question format with MC (Multiple Choice) identifier
	bb_question = 'MC\t'
	# Append the question text with a unique identifier (item_cls.item_crc16)
	question_text = clean_text_for_bbq(item_cls.question_text)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	# Shuffle choices if shuffle is enabled
	if shuffle is True:
		random.shuffle(item_cls.choices_list)
	# Loop through answer choices and format them with letters
	for i, choice_text in enumerate(item_cls.choices_list):
		letter_prefix = string_functions.number_to_letter(i+1)
		bb_question += '\t' + clean_text_for_bbq(insert_prefix_inside_div(choice_text, letter_prefix))
		# Check if the current choice is the correct answer
		if choice_text == item_cls.answer_text:
			bb_question += '\tCorrect'
		else:
			bb_question += '\tIncorrect'
	# Return the formatted question
	return bb_question + '\n'

#==============================================================
# Create a Multiple Answer (Checkboxes) question.
def MA(item_cls: item_types.MA) -> str:
	#item_number: int, item_cls.item_crc16: str, item_cls.question_text: str, item_cls.choices_list: list, item_cls.answers_list: list) -> str:
	"""Render an MA item in BBQ text upload format."""
	# Initialize the question format with MC (Multiple Answer) identifier
	bb_question = 'MA\t'
	# Append the question text with a unique identifier (item_cls.item_crc16)
	question_text = clean_text_for_bbq(item_cls.question_text)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	if shuffle is True:
		random.shuffle(item_cls.choices_list)
	# Loop through answer choices and format them with letters
	for i, choice_text in enumerate(item_cls.choices_list):
		letter_prefix = string_functions.number_to_letter(i+1)
		bb_question += '\t' + clean_text_for_bbq(insert_prefix_inside_div(choice_text, letter_prefix))
		# Check if the current choice is in the correct answer list
		if choice_text in item_cls.answers_list:
			bb_question += '\tCorrect'
		else:
			bb_question += '\tIncorrect'
	# Return the formatted question
	return bb_question + '\n'

#==============================================================
# Create a Matching question where users match items from two lists.
def MATCH(item_cls: item_types.MATCH) -> str:
	#item_number: int, item_cls.item_crc16: str, item_cls.question_text: str, item_cls.prompts_list: list, item_cls.choices_list: list) -> str:
	"""Render a MATCH item in BBQ text upload format."""
	# Initialize the question format with MAT (Matching) identifier
	bb_question = 'MAT\t'
	# Append the question text with a unique identifier (item_cls.item_crc16)
	question_text = clean_text_for_bbq(item_cls.question_text)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	# Ensure prompts and choices are the same length
	if len(item_cls.prompts_list) < len(item_cls.choices_list):
		print("Warning: bbq upload format does not allow extra distractors")
	# Loop through prompts and their matching choices
	for i in range(len(item_cls.prompts_list)):
		prompt_text = clean_text_for_bbq(item_cls.prompts_list[i])
		choice_text = clean_text_for_bbq(item_cls.choices_list[i])
		bb_question += f'\t{prompt_text}\t{choice_text}'
	# Return the formatted question
	return bb_question + '\n'

#==============================================================
# Create a Numerical question with an accepted tolerance range.
def NUM(item_cls: item_types.NUM) -> str:
	#item_number: int, item_cls.item_crc16: str,
	#item_cls.question_text: str, answer_float: float, tolerance_float: float, tol_message: bool=True) -> str:
	"""Render a NUM item in BBQ text upload format."""
	# Initialize the question format with NUM (Numerical) identifier
	bb_question = 'NUM\t'
	question_text = clean_text_for_bbq(item_cls.question_text)
	# Append optional tolerance message to question text
	if item_cls.tolerance_float is not None and item_cls.tolerance_message:
		question_text += '<p><i>Note: answers need to be within '
		if item_cls.answer_float == 0:
			question_text += f'{item_cls.tolerance_float:.8f} '
		else:
			percent = math.ceil(item_cls.tolerance_float/item_cls.answer_float*100)
			question_text += f'{percent:d}&percnt; '
		question_text += 'of the correct number to be correct.</i></p> '
	# Append question text with unique identifier (item_cls.item_crc16)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	# Append numerical answer and tolerance values
	bb_question += f'\t{item_cls.answer_float:.8f}'
	if item_cls.tolerance_float is not None:
		bb_question += f'\t{item_cls.tolerance_float:.8f}'
	# Return the formatted question
	return bb_question + '\n'

#==============================================================
# Create a Fill-in-the-Blank (Single Blank) question.
def FIB(item_cls: item_types.FIB) -> str:
	#item_number: int, item_cls.item_crc16: str, item_cls.question_text: str, item_cls.answers_list: list) -> str:
	"""Render a FIB item in BBQ text upload format."""
	# Initialize the question format with FIB (Fill in the Blank) identifier
	bb_question = 'FIB\t'
	# Append the question text with a unique identifier (item_cls.item_crc16)
	question_text = clean_text_for_bbq(item_cls.question_text)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	# Loop through possible answers and append them
	for answer_text in item_cls.answers_list:
		bb_question += f'\t{clean_text_for_bbq(answer_text)}'
	# Return the formatted question
	return bb_question + '\n'

#==============================================================
# Create a Fill-in-the-Blank (Multiple Blanks) question using answer mapping.
def MULTI_FIB(item_cls: item_types.MULTI_FIB) -> str:
	#item_number: int, item_cls.item_crc16: str, item_cls.question_text: str, answer_map: dict) -> str:
	"""Render a MULTI_FIB item in BBQ text upload format."""
	# Initialize the question format with FIB_PLUS identifier
	bb_question = 'FIB_PLUS\t'
	# Append the question text with a unique identifier (item_cls.item_crc16)
	question_text = clean_text_for_bbq(item_cls.question_text)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	# Sort and iterate through answer mappings
	keys_list = sorted(item_cls.answer_map.keys())
	for key_text in keys_list:
		bb_question += f'\t{key_text}'
		value_list = item_cls.answer_map[key_text]
		for value_text in value_list:
			bb_question += f'\t{clean_text_for_bbq(value_text)}'
		# Extra tab to denote next blank to fill-in
		bb_question += '\t'
	# Return the formatted question
	return bb_question + '\n'

#==============================================================
# Create an Ordered List question where users arrange items in a correct sequence.
def ORDER(item_cls: item_types.ORDER) -> str:
	#item_number: int, item_cls.item_crc16: str, item_cls.question_text: str, ordered_answers_list: list) -> str:
	"""Render an ORDER item in BBQ text upload format."""
	# Initialize the question format with ORD (Ordered List) identifier
	bb_question = 'ORD\t'
	# Append the question text with a unique identifier (item_cls.item_crc16)
	question_text = clean_text_for_bbq(item_cls.question_text)
	bb_question += f'<p>{item_cls.item_crc16}</p> {question_text}'
	# Append answers in correct order
	for answer_text in item_cls.ordered_answers_list:
		bb_question += f'\t{clean_text_for_bbq(answer_text)}'
	# Return the formatted question
	return bb_question + '\n'
