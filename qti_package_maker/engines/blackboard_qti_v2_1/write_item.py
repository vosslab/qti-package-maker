ENGINE_NAME = "blackboard_qti_v2_1"

# Standard Library

# Pip3 Library
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines.blackboard_qti_v2_1 import item_xml_helpers
from qti_package_maker.assessment_items import item_types

#==============================================================
def MC(item_cls: item_types.MC) -> lxml.etree.Element:
	"""Render an MC item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	# Choice identifiers in create_item_body use unpadded "answer_{idx}" (answer_1, answer_2, ...),
	# so the correctResponse value must match that exact form or Learn rejects the item with
	# mc.no_valid_answer_match. Do not zero-pad here.
	answer_id = f"answer_{item_cls.answer_index+1}"
	# takes a list as input
	response_declaration = item_xml_helpers.create_response_declaration([answer_id, ])
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body(item_cls.question_text, item_cls.choices_list, max_choices=1)
	response_processing = item_xml_helpers.create_response_processing()
	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree

#==============================================================
def MA(item_cls: item_types.MA) -> lxml.etree.Element:
	"""Render an MA item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	answer_id_list = []
	for answer_index in item_cls.answer_index_list:
		# Match the unpadded "answer_{idx}" identifiers emitted by create_item_body so Learn
		# can link each correctResponse value to a simpleChoice (no zero-padding).
		answer_id = f"answer_{answer_index+1}"
		answer_id_list.append(answer_id)
	# sort numerically by choice index so double-digit ids (answer_10) order after answer_2
	answer_id_list.sort(key=lambda answer_id: int(answer_id.rsplit("_", 1)[1]))
	response_declaration = item_xml_helpers.create_response_declaration(answer_id_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body(item_cls.question_text,
		item_cls.choices_list, max_choices=len(item_cls.answers_list))
	response_processing = item_xml_helpers.create_response_processing()
	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree

#==============================================================
def MATCH(item_cls: item_types.MATCH) -> lxml.etree.Element:
	#crc16_text: str, question_text: str, answers_list: list, matching_list: list):
	"""Render a MATCH item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	response_declaration = item_xml_helpers.create_response_declaration_MATCH(item_cls.prompts_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_MATCH(item_cls.question_text,
		item_cls.prompts_list, item_cls.choices_list, shuffle=True)
	response_processing = item_xml_helpers.create_response_processing_MATCH()
	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree

#==============================================================
def NUM(item_cls: item_types.NUM) -> lxml.etree.Element:
	#crc16_text: str, question_text: str, answer: float, tolerance: float, tol_message=True):
	"""Render a NUM item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	response_declaration = item_xml_helpers.create_response_declaration_NUM(item_cls.answer_float)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_NUM(item_cls.question_text)
	response_processing = item_xml_helpers.create_response_processing_NUM(
		item_cls.answer_float, item_cls.tolerance_float,
		tolerance_mode="absolute",
		include_lower=True, include_upper=True)
	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree

#==============================================================
def FIB(item_cls: item_types.FIB) -> lxml.etree.Element:
	#crc16_text: str, question_text: str, answers_list: list):
	"""Render a FIB item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	# takes a list as input
	response_declaration = item_xml_helpers.create_response_declaration_FIB(item_cls.answers_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_FIB(item_cls.question_text, item_cls.answers_list)
	response_processing = item_xml_helpers.create_response_processing()
	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree

#==============================================================
def MULTI_FIB(item_cls: item_types.MULTI_FIB) -> lxml.etree.Element:
	#crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""Render a MULTI_FIB item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	response_declarations = item_xml_helpers.create_response_declarations_MULTI_FIB(item_cls.answer_map)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_MULTI_FIB(item_cls.question_text, item_cls.answer_map)
	response_processing = item_xml_helpers.create_response_processing_MULTI_FIB(item_cls.answer_map)
	assessment_item_etree.extend(response_declarations)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree

#==============================================================
def ORDER(item_cls: item_types.ORDER) -> lxml.etree.Element:
	#crc16_text: str, question_text: str, ordered_answers_list: list):
	"""Render an ORDER item as Blackboard QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)
	response_declaration = item_xml_helpers.create_response_declaration_ORDER(item_cls.ordered_answers_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_ORDER(item_cls.question_text, item_cls.ordered_answers_list, shuffle=True)
	response_processing = item_xml_helpers.create_response_processing_ORDER()
	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)
	return assessment_item_etree
