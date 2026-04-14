"""Ultra-specific QTI element builders for Blackboard Ultra QTI 2.1."""

import html

# PIP3 modules
import lxml.html
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines.bb_ultra_qti_v2_1 import html_sanitize
from qti_package_maker.engines.blackboard_qti_v2_1 import item_xml_helpers as learn_helpers


#============================================
def create_assessment_item_header(item_crc16: str) -> lxml.etree.Element:
	"""
	Create the root <assessmentItem> element with Ultra-specific namespaces and identifier.

	Ultra identifier format: QUE__<crc16_collapsed>_1
	where crc16_collapsed is the CRC16 with underscores removed.

	Args:
		item_crc16: Item CRC16 string (e.g., "1234_5678").

	Returns:
		lxml.etree.Element: The root <assessmentItem> element.
	"""
	# Strip underscores from CRC16 to create the identifier
	crc16_collapsed = str(item_crc16).replace('_', '')
	identifier = f"QUE__{crc16_collapsed}_1"

	# Define all required XML namespaces for Ultra
	nsmap = {
		None: "http://www.imsglobal.org/xsd/imsqti_v2p1",
		"ns9": "http://www.imsglobal.org/xsd/apip/apipv1p0/imsapip_qtiv1p0",
		"ns8": "http://www.w3.org/1999/xlink",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance",
	}

	# Create the root <assessmentItem> element with Ultra attributes
	item_tree = lxml.etree.Element(
		"assessmentItem",
		nsmap=nsmap,
		attrib={
			"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
				"http://www.imsglobal.org/xsd/imsqti_v2p1 "
				"http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"
			),
			"adaptive": "false",
			"timeDependent": "false",
			"identifier": identifier,
		},
	)
	return item_tree


#============================================
def create_response_declaration(correct_values: list) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for MC/MA with Ultra cardinality.

	Ultra always uses cardinality="multiple" and baseType="identifier",
	even for single-answer MC.

	Args:
		correct_values: List of correct answer identifiers (e.g., ["answer_1"]).

	Returns:
		lxml.etree.Element: The <responseDeclaration> element.
	"""
	response_declaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"cardinality": "multiple",
			"baseType": "identifier",
			"identifier": "RESPONSE",
		},
	)
	correct_response = lxml.etree.SubElement(response_declaration, "correctResponse")
	for value in correct_values:
		lxml.etree.SubElement(correct_response, "value").text = value
	return response_declaration


#============================================
def create_response_declaration_FIB(answers_list: list) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for FIB items.

	Args:
		answers_list: List of correct answer strings.

	Returns:
		lxml.etree.Element: The <responseDeclaration> element.
	"""
	response_declaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"baseType": "string",
			"cardinality": "single",
			"identifier": "RESPONSE",
		},
	)
	correct_response = lxml.etree.SubElement(response_declaration, "correctResponse")
	mapping = lxml.etree.SubElement(response_declaration, "mapping")
	for value in answers_list:
		lxml.etree.SubElement(correct_response, "value").text = value
		lxml.etree.SubElement(mapping, "mapEntry", {
			"mapKey": value,
			"caseSensitive": "false",
			"mappedValue": "100.0",
		})
	return response_declaration


#============================================
def create_response_declaration_NUM(answer_float: float) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for NUM items.

	Args:
		answer_float: The correct numeric answer.

	Returns:
		lxml.etree.Element: The <responseDeclaration> element.
	"""
	response_declaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"baseType": "float",
			"cardinality": "single",
			"identifier": "RESPONSE",
		},
	)
	correct_response = lxml.etree.SubElement(response_declaration, "correctResponse")
	lxml.etree.SubElement(correct_response, "value").text = str(answer_float)
	return response_declaration


#============================================
def create_response_declaration_MULTI_FIB(answer_map: dict) -> list:
	"""
	Create <responseDeclaration> elements for MULTI_FIB items (one per blank).

	Args:
		answer_map: Dictionary mapping response identifiers to answer lists.

	Returns:
		list: List of <responseDeclaration> elements.
	"""
	response_declarations = []
	for key, answers in answer_map.items():
		resp_decl = lxml.etree.Element(
			"responseDeclaration",
			attrib={
				"baseType": "string",
				"cardinality": "single",
				"identifier": key,
			},
		)
		correct_response = lxml.etree.SubElement(resp_decl, "correctResponse")
		for val in answers:
			lxml.etree.SubElement(correct_response, "value").text = val
		response_declarations.append(resp_decl)
	return response_declarations


#============================================
def create_response_declaration_MATCH(prompts_list: list) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for MATCH items.

	Uses directedPair baseType with unpadded prompt/choice identifiers.

	Args:
		prompts_list: List of prompt texts.

	Returns:
		lxml.etree.Element: The <responseDeclaration> element.
	"""
	response_declaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"baseType": "directedPair",
			"cardinality": "multiple",
			"identifier": "RESPONSE",
		},
	)

	correct_response = lxml.etree.SubElement(response_declaration, "correctResponse")
	mapping = lxml.etree.SubElement(response_declaration, "mapping", defaultValue="0")

	for idx in range(len(prompts_list)):
		prompt_id = f"prompt_{idx+1}"
		choice_id = f"choice_{idx+1}"
		pair_value = f"{prompt_id} {choice_id}"
		lxml.etree.SubElement(correct_response, "value").text = pair_value
		lxml.etree.SubElement(mapping, "mapEntry", mapKey=pair_value, mappedValue="1")

	return response_declaration


#============================================
def create_item_body(question_html: str, choices_list: list, max_choices: int) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for MC/MA with Ultra's double-div wrapping.

	Ultra expects the question wrapped in <div><div>...</div></div>,
	and each choice wrapped in <div><p>...</p></div>.

	Args:
		question_html: HTML string for the question.
		choices_list: List of choice HTML strings.
		max_choices: Maximum number of choices (1 for MC, >1 for MA).

	Returns:
		lxml.etree.Element: The <itemBody> element.
	"""
	item_body = lxml.etree.Element("itemBody")

	# Sanitize question HTML
	sanitized_question = html_sanitize.sanitize_fragment(question_html)
	unescaped_question = html.unescape(sanitized_question)

	# Parse sanitized question and wrap in double-div
	inner_div = lxml.html.fragment_fromstring(unescaped_question, create_parent='div')
	outer_div = lxml.etree.Element("div")
	outer_div.append(inner_div)
	item_body.append(outer_div)

	# Create <choiceInteraction> with unpadded answer identifiers
	choice_interaction = lxml.etree.SubElement(item_body, "choiceInteraction", {
		"responseIdentifier": "RESPONSE",
		"maxChoices": str(max_choices),
		"shuffle": "false",
	})

	for idx, choice_html in enumerate(choices_list, start=1):
		simple_choice = lxml.etree.SubElement(choice_interaction, "simpleChoice", {
			"identifier": f"answer_{idx}",
			"fixed": "true",
		})

		# Sanitize choice HTML
		sanitized_choice = html_sanitize.sanitize_fragment(choice_html)
		unescaped_choice = html.unescape(sanitized_choice)

		# Wrap choice in <div><p>...</p></div>
		p_elem = lxml.html.fragment_fromstring(unescaped_choice, create_parent='p')
		choice_div = lxml.etree.Element("div")
		choice_div.append(p_elem)
		simple_choice.append(choice_div)

	return item_body


#============================================
def create_item_body_FIB(question_html: str) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for FIB items.

	Args:
		question_html: HTML string for the question.

	Returns:
		lxml.etree.Element: The <itemBody> element.
	"""
	item_body = lxml.etree.Element("itemBody")

	# Sanitize question HTML
	sanitized_question = html_sanitize.sanitize_fragment(question_html)
	unescaped_question = html.unescape(sanitized_question)

	# Parse and wrap in double-div
	inner_div = lxml.html.fragment_fromstring(unescaped_question, create_parent='div')
	outer_div = lxml.etree.Element("div")
	outer_div.append(inner_div)
	item_body.append(outer_div)

	# Create textEntryInteraction
	text_entry_p = lxml.etree.SubElement(item_body, "p")
	lxml.etree.SubElement(text_entry_p, "textEntryInteraction", {
		"responseIdentifier": "RESPONSE",
	})

	return item_body


#============================================
def create_item_body_NUM(question_html: str) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for NUM items.

	Args:
		question_html: HTML string for the question.

	Returns:
		lxml.etree.Element: The <itemBody> element.
	"""
	item_body = lxml.etree.Element("itemBody")

	# Sanitize question HTML
	sanitized_question = html_sanitize.sanitize_fragment(question_html)
	unescaped_question = html.unescape(sanitized_question)

	# Parse and wrap in double-div
	inner_div = lxml.html.fragment_fromstring(unescaped_question, create_parent='div')
	outer_div = lxml.etree.Element("div")
	outer_div.append(inner_div)
	item_body.append(outer_div)

	# Create textEntryInteraction
	text_entry_p = lxml.etree.SubElement(item_body, "p")
	lxml.etree.SubElement(text_entry_p, "textEntryInteraction", {
		"responseIdentifier": "RESPONSE",
	})

	return item_body


#============================================
def create_item_body_MULTI_FIB(question_html: str, answer_map: dict) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for MULTI_FIB items.

	Replaces [key] markers with textEntryInteraction elements.

	Args:
		question_html: HTML string with [key] placeholders.
		answer_map: Dictionary mapping keys to answer lists.

	Returns:
		lxml.etree.Element: The <itemBody> element.
	"""
	item_body = lxml.etree.Element("itemBody")

	# Sanitize question HTML
	sanitized_question = html_sanitize.sanitize_fragment(question_html)
	unescaped_question = html.unescape(sanitized_question)

	# Replace [key] placeholders with textEntryInteraction elements
	for key in sorted(answer_map.keys()):
		placeholder = f"[{key}]"
		interaction = f'<textEntryInteraction responseIdentifier="{key}"></textEntryInteraction>'
		unescaped_question = unescaped_question.replace(placeholder, interaction)

	# Parse and wrap in double-div
	inner_div = lxml.html.fragment_fromstring(unescaped_question, create_parent='div')
	outer_div = lxml.etree.Element("div")
	outer_div.append(inner_div)
	item_body.append(outer_div)

	return item_body


#============================================
def create_item_body_MATCH(question_html: str, prompts_list: list, choices_list: list) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for MATCH items.

	Uses unpadded prompt_N and choice_N identifiers.

	Args:
		question_html: HTML string for the question stem.
		prompts_list: List of prompt texts to match.
		choices_list: List of choice texts to match with.

	Returns:
		lxml.etree.Element: The <itemBody> element.
	"""
	item_body = lxml.etree.Element("itemBody")

	# Sanitize question HTML
	sanitized_question = html_sanitize.sanitize_fragment(question_html)
	unescaped_question = html.unescape(sanitized_question)

	# Parse and wrap in double-div
	inner_div = lxml.html.fragment_fromstring(unescaped_question, create_parent='div')
	outer_div = lxml.etree.Element("div")
	outer_div.append(inner_div)
	item_body.append(outer_div)

	# Create matchInteraction
	match_interaction = lxml.etree.SubElement(item_body, "matchInteraction", {
		"responseIdentifier": "RESPONSE",
		"shuffle": "false",
		"maxAssociations": str(len(prompts_list)),
	})

	# Prompts (left side)
	prompt_set = lxml.etree.SubElement(match_interaction, "simpleMatchSet")
	for idx, prompt_text in enumerate(prompts_list, start=1):
		prompt_choice = lxml.etree.SubElement(prompt_set, "simpleAssociableChoice", {
			"identifier": f"prompt_{idx}",
			"fixed": "true",
			"matchMax": "1",
			"matchMin": "0",
		})

		# Sanitize and wrap prompt
		sanitized_prompt = html_sanitize.sanitize_fragment(prompt_text)
		unescaped_prompt = html.unescape(sanitized_prompt)
		parsed_prompt = lxml.html.fragment_fromstring(unescaped_prompt, create_parent='p')
		prompt_choice.append(parsed_prompt)

	# Choices (right side)
	choice_set = lxml.etree.SubElement(match_interaction, "simpleMatchSet")
	for idx, choice_text in enumerate(choices_list, start=1):
		choice = lxml.etree.SubElement(choice_set, "simpleAssociableChoice", {
			"identifier": f"choice_{idx}",
			"fixed": "true",
			"matchMax": str(len(prompts_list)),
			"matchMin": "0",
		})

		# Sanitize and wrap choice
		sanitized_choice = html_sanitize.sanitize_fragment(choice_text)
		unescaped_choice = html.unescape(sanitized_choice)
		parsed_choice = lxml.html.fragment_fromstring(unescaped_choice, create_parent='p')
		choice.append(parsed_choice)

	return item_body


#============================================
def create_outcome_declarations() -> list:
	"""
	Create the standard outcome declarations for Ultra.

	Delegates to the Learn engine's create_outcome_declarations_big()
	which provides SCORE, FEEDBACKBASIC, and MAXSCORE.

	Returns:
		list: List of <outcomeDeclaration> elements.
	"""
	return learn_helpers.create_outcome_declarations_big()


#============================================
def create_response_processing() -> lxml.etree.Element:
	"""
	Create the standard response processing for Ultra.

	Delegates to the Learn engine's create_response_processing_big()
	which provides full responseIf/responseElse with feedback.

	Returns:
		lxml.etree.Element: The <responseProcessing> element.
	"""
	return learn_helpers.create_response_processing_big()


#============================================
def create_response_processing_MULTI_FIB(answer_map: dict) -> lxml.etree.Element:
	"""
	Create <responseProcessing> for MULTI_FIB with partial credit.

	Args:
		answer_map: Dictionary mapping response identifiers to answer lists.

	Returns:
		lxml.etree.Element: The <responseProcessing> element.
	"""
	response_processing = lxml.etree.Element("responseProcessing")
	blanks = list(sorted(answer_map.keys()))
	base_score = 100 / len(blanks) if blanks else 0

	for key in blanks:
		resp_condition = lxml.etree.SubElement(response_processing, "responseCondition")
		resp_if = lxml.etree.SubElement(resp_condition, "responseIf")

		# Match the correct response for this blank
		match = lxml.etree.SubElement(resp_if, "match")
		lxml.etree.SubElement(match, "variable", {"identifier": key})
		lxml.etree.SubElement(match, "correct", {"identifier": key})

		# Set outcome for correct response
		set_outcome = lxml.etree.SubElement(resp_if, "setOutcomeValue", {"identifier": "SCORE"})
		lxml.etree.SubElement(set_outcome, "baseValue", {"baseType": "float"}).text = str(base_score)

	return response_processing


#============================================
def create_response_processing_MATCH() -> lxml.etree.Element:
	"""
	Create <responseProcessing> for MATCH items using template.

	Returns:
		lxml.etree.Element: The <responseProcessing> element.
	"""
	return lxml.etree.Element("responseProcessing", {
		"template": "http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response",
	})


#============================================
def create_response_processing_NUM(answer_float: float, tolerance_float: float,
		tolerance_mode: str = "absolute",
		include_lower: bool = True, include_upper: bool = True) -> lxml.etree.Element:
	"""
	Create <responseProcessing> for NUM items with tolerance.

	Args:
		answer_float: The correct numeric answer.
		tolerance_float: The tolerance amount.
		tolerance_mode: "absolute" or "relative".
		include_lower: Whether to include the lower bound.
		include_upper: Whether to include the upper bound.

	Returns:
		lxml.etree.Element: The <responseProcessing> element.
	"""
	response_processing = lxml.etree.Element("responseProcessing")
	response_condition = lxml.etree.SubElement(response_processing, "responseCondition")
	response_if = lxml.etree.SubElement(response_condition, "responseIf")

	# Match with tolerance
	tolerance_str = f"{tolerance_float} {tolerance_float}"
	equal = lxml.etree.SubElement(response_if, "equal", {
		"toleranceMode": tolerance_mode,
		"tolerance": tolerance_str,
		"includeLowerBound": str(include_lower).lower(),
		"includeUpperBound": str(include_upper).lower(),
	})
	lxml.etree.SubElement(equal, "variable", {"identifier": "RESPONSE"})
	lxml.etree.SubElement(equal, "correct", {"identifier": "RESPONSE"})

	# Set score to MAXSCORE if correct
	set_outcome = lxml.etree.SubElement(response_if, "setOutcomeValue", {"identifier": "SCORE"})
	lxml.etree.SubElement(set_outcome, "variable", {"identifier": "MAXSCORE"})

	# Set feedback for correct
	set_feedback = lxml.etree.SubElement(response_if, "setOutcomeValue", {"identifier": "FEEDBACKBASIC"})
	lxml.etree.SubElement(set_feedback, "baseValue", {"baseType": "identifier"}).text = "correct_fb"

	# Else: set incorrect feedback
	response_else = lxml.etree.SubElement(response_condition, "responseElse")
	set_feedback_else = lxml.etree.SubElement(response_else, "setOutcomeValue", {"identifier": "FEEDBACKBASIC"})
	lxml.etree.SubElement(set_feedback_else, "baseValue", {"baseType": "identifier"}).text = "incorrect_fb"

	return response_processing
