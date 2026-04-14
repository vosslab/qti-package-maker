"""Per-item-type dispatch functions for Blackboard Ultra QTI 2.1 engine."""

ENGINE_NAME = "bb_ultra_qti_v2_1"

# QTI Package Maker
from qti_package_maker.engines.bb_ultra_qti_v2_1 import item_xml_helpers


#==============================================================================
def MC(item_cls):
	"""Render an MC item as Blackboard Ultra QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)

	# Build correct answer identifier (unpadded)
	answer_id = f"answer_{item_cls.answer_index + 1}"
	response_declaration = item_xml_helpers.create_response_declaration([answer_id])

	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body(
		item_cls.question_text,
		item_cls.choices_list,
		max_choices=1
	)
	response_processing = item_xml_helpers.create_response_processing()

	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)

	return assessment_item_etree


#==============================================================================
def MA(item_cls):
	"""Render an MA item as Blackboard Ultra QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)

	# Build list of correct answer identifiers (unpadded)
	answer_id_list = []
	for answer_index in item_cls.answer_index_list:
		answer_id = f"answer_{answer_index + 1}"
		answer_id_list.append(answer_id)
	answer_id_list.sort()

	response_declaration = item_xml_helpers.create_response_declaration(answer_id_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body(
		item_cls.question_text,
		item_cls.choices_list,
		max_choices=len(item_cls.answers_list)
	)
	response_processing = item_xml_helpers.create_response_processing()

	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)

	return assessment_item_etree


#==============================================================================
def FIB(item_cls):
	"""Render a FIB item as Blackboard Ultra QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)

	response_declaration = item_xml_helpers.create_response_declaration_FIB(item_cls.answers_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_FIB(item_cls.question_text)
	response_processing = item_xml_helpers.create_response_processing()

	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)

	return assessment_item_etree


#==============================================================================
def NUM(item_cls):
	"""Render a NUM item as Blackboard Ultra QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)

	response_declaration = item_xml_helpers.create_response_declaration_NUM(item_cls.answer_float)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_NUM(item_cls.question_text)
	response_processing = item_xml_helpers.create_response_processing_NUM(
		item_cls.answer_float,
		item_cls.tolerance_float,
		tolerance_mode="absolute",
		include_lower=True,
		include_upper=True
	)

	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)

	return assessment_item_etree


#==============================================================================
def MULTI_FIB(item_cls):
	"""Render a MULTI_FIB item as Blackboard Ultra QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)

	response_declarations = item_xml_helpers.create_response_declaration_MULTI_FIB(item_cls.answer_map)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_MULTI_FIB(
		item_cls.question_text,
		item_cls.answer_map
	)
	response_processing = item_xml_helpers.create_response_processing_MULTI_FIB(item_cls.answer_map)

	# Assemble the XML tree
	assessment_item_etree.extend(response_declarations)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)

	return assessment_item_etree


#==============================================================================
def MATCH(item_cls):
	"""Render a MATCH item as Blackboard Ultra QTI 2.1 XML."""
	assessment_item_etree = item_xml_helpers.create_assessment_item_header(item_cls.item_crc16)

	response_declaration = item_xml_helpers.create_response_declaration_MATCH(item_cls.prompts_list)
	outcome_declarations = item_xml_helpers.create_outcome_declarations()
	item_body = item_xml_helpers.create_item_body_MATCH(
		item_cls.question_text,
		item_cls.prompts_list,
		item_cls.choices_list
	)
	response_processing = item_xml_helpers.create_response_processing_MATCH()

	# Assemble the XML tree
	assessment_item_etree.append(response_declaration)
	for outcome in outcome_declarations:
		assessment_item_etree.append(outcome)
	assessment_item_etree.append(item_body)
	assessment_item_etree.append(response_processing)

	return assessment_item_etree
