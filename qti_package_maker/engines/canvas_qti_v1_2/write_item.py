ENGINE_NAME = "canvas_qti_v1_2"

# Standard Library

# Pip3 Library
import lxml.etree

# QTI Package Maker
#from qti_package_maker.common import string_functions
from qti_package_maker.engines.canvas_qti_v1_2 import item_xml_helpers
from qti_package_maker.assessment_items import item_types

#==============================================================
def MC(item_cls: item_types.MC) -> lxml.etree.Element:
	#crc16_text: str, question_text: str, choices_list: list, answer_text: str):
	"""Render an MC item as Canvas QTI 1.2 XML."""
	# Create the root <item> element with a unique identifier and title
	assessment_item_etree = lxml.etree.Element("item",
			ident=f"multiple_choice_{item_cls.item_number:03d}", title=item_cls.item_crc16)
	# Generate the <itemmetadata> section to store metadata about the question
	choice_ids_list = [f"choice_{i+1:03d}" for i in range(len(item_cls.choices_list))]
	itemmetadata = item_xml_helpers.create_itemmetadata(choice_ids_list, 'multiple_choice_question')
	# Create the <presentation> section to hold the question text and answer choices
	presentation_etree = lxml.etree.Element("presentation")
	# Generate the <material> section containing the question text
	material_mattext_etree = item_xml_helpers.create_material_mattext(item_cls.question_text)
	# Generate the <response_lid> section to store answer choices (radio buttons)
	response_lid_etree = item_xml_helpers.create_choice_response_lid(item_cls.choices_list, cardinality="Single")
	# Generate the <resprocessing> section to handle scoring and correctness logic
	resprocessing_etree = item_xml_helpers.create_MC_resprocessing(item_cls.choices_list, item_cls.answer_text)
	# Assemble the XML structure by appending elements in the correct order
	presentation_etree.append(material_mattext_etree)
	presentation_etree.append(response_lid_etree)
	assessment_item_etree.append(itemmetadata)
	assessment_item_etree.append(presentation_etree)
	assessment_item_etree.append(resprocessing_etree)
	# Return the fully assembled XML tree for the question
	return assessment_item_etree

#==============================================================
def MA(item_cls: item_types.MA) -> lxml.etree.Element:
	#item_number: int, crc16_text: str, question_text: str, choices_list: list, answers_list: list):
	"""Render an MA item as Canvas QTI 1.2 XML."""
	# Create the root <item> element with a unique identifier and title
	assessment_item_etree = lxml.etree.Element("item",
		ident=f"multiple_answer_{item_cls.item_number:03d}", title=item_cls.item_crc16)
	# Generate the <itemmetadata> section to store metadata about the question
	choice_ids_list = [f"choice_{i+1:03d}" for i in range(len(item_cls.choices_list))]
	itemmetadata = item_xml_helpers.create_itemmetadata(choice_ids_list, 'multiple_answers_question')
	# Create the <presentation> section to hold the question text and answer choices
	presentation_etree = lxml.etree.Element("presentation")
	# Generate the <material> section containing the question text
	material_mattext_etree = item_xml_helpers.create_material_mattext(item_cls.question_text)
	# Generate the <response_lid> section to store answer choices (checkboxes)
	response_lid_etree = item_xml_helpers.create_choice_response_lid(item_cls.choices_list, cardinality="Multiple")
	# Generate the <resprocessing> section to handle scoring and correctness logic
	resprocessing_etree = item_xml_helpers.create_MA_resprocessing(item_cls.choices_list, item_cls.answers_list)
	# Assemble the XML structure by appending elements in the correct order
	presentation_etree.append(material_mattext_etree)
	presentation_etree.append(response_lid_etree)
	assessment_item_etree.append(itemmetadata)
	assessment_item_etree.append(presentation_etree)
	assessment_item_etree.append(resprocessing_etree)
	# Return the fully assembled XML tree for the question
	return assessment_item_etree

#==============================================================
def MATCH(item_cls: item_types.MATCH) -> lxml.etree.Element:
	#item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""Render a MATCH item as Canvas QTI 1.2 XML."""
	# Create the root <item> element with a unique identifier and title
	assessment_item_etree = lxml.etree.Element("item",
		ident=f"matching_{item_cls.item_number:03d}", title=item_cls.item_crc16)
	# Generate the <itemmetadata> section for metadata
	choice_ids_list = [f"{i+1:03d}" for i in range(len(item_cls.choices_list))]
	itemmetadata = item_xml_helpers.create_itemmetadata(choice_ids_list, 'matching_question')
	# Create the <presentation> section for question text and matching choices
	presentation_etree = lxml.etree.Element("presentation")
	# Generate the <material> section containing the question text
	material_mattext_etree = item_xml_helpers.create_material_mattext(item_cls.question_text)
	# Generate <response_lid> sections for each answer item
	response_lids_etree = item_xml_helpers.create_matching_response_lid(item_cls.prompts_list, item_cls.choices_list)
	# Generate the <resprocessing> section for scoring
	resprocessing_etree = item_xml_helpers.create_MATCH_resprocessing(item_cls.prompts_list)
	# Assemble the XML structure by appending elements in the correct order
	presentation_etree.append(material_mattext_etree)
	for response_lid in response_lids_etree:
		presentation_etree.append(response_lid)
	assessment_item_etree.append(itemmetadata)
	assessment_item_etree.append(presentation_etree)
	assessment_item_etree.append(resprocessing_etree)
	# Return the fully assembled XML tree for the question
	return assessment_item_etree

#==============================================================
def NUM(item_cls: item_types.NUM) -> lxml.etree.Element:
	#item_number: int, crc16_text: str, question_text: str, answer: float, tolerance: float, tol_message=True):
	"""Render a NUM item as Canvas QTI 1.2 XML."""
	assessment_item_etree = lxml.etree.Element("item",
		ident=f"numeric_{item_cls.item_number:03d}", title=item_cls.item_crc16)
	# Minimal metadata
	itemmetadata = item_xml_helpers.create_itemmetadata([], 'numerical_question')
	presentation_etree = item_xml_helpers.create_numeric_presentation(item_cls.question_text)
	resprocessing_etree = item_xml_helpers.create_NUM_resprocessing(item_cls.answer_float, item_cls.tolerance_float)
	assessment_item_etree.append(itemmetadata)
	assessment_item_etree.append(presentation_etree)
	assessment_item_etree.append(resprocessing_etree)
	return assessment_item_etree

#==============================================================
def FIB(item_cls: item_types.FIB) -> lxml.etree.Element:
	#item_number: int, crc16_text: str, question_text: str, answers_list: list):
	"""Render a FIB item as Canvas QTI 1.2 XML."""
	assessment_item_etree = lxml.etree.Element("item",
		ident=f"fib_{item_cls.item_number:03d}", title=item_cls.item_crc16)
	itemmetadata = item_xml_helpers.create_itemmetadata([], 'short_answer_question')
	presentation_etree = item_xml_helpers.create_fib_presentation(item_cls.question_text)
	resprocessing_etree = item_xml_helpers.create_FIB_resprocessing(item_cls.answers_list)
	assessment_item_etree.append(itemmetadata)
	assessment_item_etree.append(presentation_etree)
	assessment_item_etree.append(resprocessing_etree)
	return assessment_item_etree

#==============================================================
def MULTI_FIB(item_cls: item_types.MULTI_FIB) -> lxml.etree.Element:
	#item_number: int, crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""Render a MULTI_FIB item as Canvas QTI 1.2 XML."""
	assessment_item_etree = lxml.etree.Element("item",
		ident=f"fib_multi_{item_cls.item_number:03d}", title=item_cls.item_crc16)
	_, label_ids = item_xml_helpers.create_multi_fib_response_lids(item_cls.answer_map)
	choice_ids_list = label_ids
	itemmetadata = item_xml_helpers.create_itemmetadata(choice_ids_list, 'fill_in_multiple_blanks_question')
	presentation_etree = item_xml_helpers.create_multi_fib_presentation(item_cls.question_text, item_cls.answer_map)
	resprocessing_etree = item_xml_helpers.create_MULTI_FIB_resprocessing(item_cls.answer_map)
	assessment_item_etree.append(itemmetadata)
	assessment_item_etree.append(presentation_etree)
	assessment_item_etree.append(resprocessing_etree)
	return assessment_item_etree

#==============================================================
def ORDER(item_cls: item_types.ORDER) -> None:
	#item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	"""Canvas QTI 1.2 writer does not implement ORDER items."""
	raise NotImplementedError
