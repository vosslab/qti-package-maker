
import html
import random

# PIP3 modules
import lxml.html
import lxml.etree

#==============
def create_assessment_item_header(question_crc16: str) -> lxml.etree.Element:
	"""
	Create the root <assessmentItem> element with common namespaces and attributes.
	"""
	rand_crc16 = f"{random.randrange(16**4):04x}"
	# "QUE_" prefix keeps this a legal xs:NCName (identifier.type in the QTI
	# 2.1 schema): question_crc16/rand_crc16 are hex digits and could
	# otherwise start with a digit, which xs:NCName forbids. The "QUE_"
	# shape also matches the real item identifier prefix confirmed by
	# SAMPLES/blackboard_learn_classic-qti21_export (e.g. "QUE__23221280_1").
	identifier = f"QUE_{question_crc16}_{rand_crc16}"
	item_title = identifier
	# Define all required XML namespaces, including the missing ones
	nsmap = {
		None: "http://www.imsglobal.org/xsd/imsqti_v2p1",  # Default namespace
		"xsi": "http://www.w3.org/2001/XMLSchema-instance",
		"ns8": "http://www.w3.org/1999/xlink",
		"ns9": "http://www.imsglobal.org/xsd/apip/apipv1p0/imsapip_qtiv1p0"
	}
	# Create the root <assessmentItem> element with required attributes
	item_tree = lxml.etree.Element(
		"assessmentItem",
		nsmap=nsmap,
		attrib={
			"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
				"http://www.imsglobal.org/xsd/imsqti_v2p1 "
				"http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"
			),
			"title": item_title,
			"adaptive": "false",
			"timeDependent": "false",
			"identifier": identifier,
		},
	)
	return item_tree

#==============
def create_response_declaration(correct_values: list) -> lxml.etree.Element:
	## IMPORTANT !!!
	"""
	Create a <responseDeclaration> element.
	Returns:
		lxml.etree.Element: The <responseDeclaration> element.
  <responseDeclaration cardinality="multiple" baseType="identifier" identifier="RESPONSE">
    <correctResponse>
      <value>answer_1</value>
      <value>answer_2</value>
    </correctResponse>
  </responseDeclaration>
	"""
	responseDeclaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"baseType": "identifier",
			"cardinality": "single" if len(correct_values) == 1 else "multiple",
			"identifier": "RESPONSE",
		},
	)
	correct_response = lxml.etree.SubElement(responseDeclaration, "correctResponse")
	for value in correct_values:
		lxml.etree.SubElement(correct_response, "value").text = value
	return responseDeclaration

#==============
def create_response_declaration_FIB(answers_list: list) -> lxml.etree.Element:
	## IMPORTANT !!!
	responseDeclaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"baseType": "string",
			"cardinality": "single",
			"identifier": "RESPONSE",
		},
	)
	# Create <correctResponse> and <mapping>
	correct_response = lxml.etree.SubElement(responseDeclaration, "correctResponse")
	mapping = lxml.etree.SubElement(responseDeclaration, "mapping")
	# Iterate once to create both <value> and <mapEntry>
	for value in answers_list:
		lxml.etree.SubElement(correct_response, "value").text = value
		lxml.etree.SubElement(mapping, "mapEntry", {
			"mapKey": value,
			"caseSensitive": "false",
			"mappedValue": "100.0",
		})
	return responseDeclaration

#==============
def create_response_declaration_MATCH(prompts_list: list) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for matching interactions following the
	1EdTech QTI 2.1 match example (directed pairs, multiple cardinality, mapped scoring).
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
		prompt_id = f"prompt_{idx+1:03d}"
		choice_id = f"choice_{idx+1:03d}"
		pair_value = f"{prompt_id} {choice_id}"
		lxml.etree.SubElement(correct_response, "value").text = pair_value
		lxml.etree.SubElement(mapping, "mapEntry", mapKey=pair_value, mappedValue="1")

	return response_declaration

#==============
def create_item_body(
		question_html_text: str, choices_list: list, max_choices: int, shuffle: bool=True
		) -> lxml.etree.Element:
	## IMPORTANT !!!
	"""
	Create the <itemBody> element with the question text and choices.
	"""
	item_body = lxml.etree.Element("itemBody")

	unescaped_text = html.unescape(question_html_text)
	parsed_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='div')
	#if len(parsed_html.getchildren()) > 1:
	#	raise ValueError(f"Question text contains multiple elements: {unescaped_text}")
	item_body.append(parsed_html)

	# Create <choiceInteraction> with proper attributes
	choice_interaction = lxml.etree.SubElement(item_body, "choiceInteraction", {
		"maxChoices": f"{max_choices:d}",
		"responseIdentifier": "RESPONSE",
		"shuffle": str(shuffle).lower(),
	})
	# Add choices without extra <p> tags
	for idx, choice_html_text in enumerate(choices_list, start=1):
		simple_choice = lxml.etree.SubElement(
			choice_interaction, "simpleChoice",
			{
				"fixed": "true",
				"identifier": f"answer_{idx}",
			}
		)
		# Unescape choice text
		unescaped_text = html.unescape(choice_html_text)
		# Ensure choice text is wrapped in <p>
		parsed_choice_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='p')
		# Ensure the parsed choice has only one top-level <p> element
		#if len(parsed_choice_html.getchildren()) > 1:
		#	raise ValueError(f"Choice text contains multiple elements: {choice_html_text}")
		# Append the single <p> element inside <simpleChoice>
		simple_choice.append(parsed_choice_html)
	return item_body

#==============
def create_item_body_FIB(question_html_text: str, choices_list: list) -> lxml.etree.Element:
	## IMPORTANT !!!
	"""
	Create the <itemBody> element with the question text and choices.
	"""
	item_body = lxml.etree.Element("itemBody")

	unescaped_text = html.unescape(question_html_text)
	parsed_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='div')
	#if len(parsed_html.getchildren()) > 1:
	#	raise ValueError(f"Question text contains multiple elements: {question_html_text}")
	item_body.append(parsed_html)

	# Create a <p> wrapper for the <textEntryInteraction> field
	text_entry_p = lxml.etree.SubElement(item_body, "p")
	# Create the <textEntryInteraction> element inside <p>
	lxml.etree.SubElement(text_entry_p, "textEntryInteraction", {
		"responseIdentifier": "RESPONSE"
	})

	return item_body

#==============
def create_item_body_MATCH(question_html_text: str, prompts_list: list, choices_list: list,
		shuffle: bool=True) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for a matching interaction.
	"""
	item_body = lxml.etree.Element("itemBody")

	unescaped_text = html.unescape(question_html_text)
	parsed_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='div')
	item_body.append(parsed_html)

	match_interaction = lxml.etree.SubElement(item_body, "matchInteraction", {
		"responseIdentifier": "RESPONSE",
		"shuffle": str(shuffle).lower(),
		"maxAssociations": f"{len(prompts_list):d}",
	})
	# Optional prompt that mirrors the question stem for compatibility with reference examples
	lxml.etree.SubElement(match_interaction, "prompt").text = html.unescape(question_html_text)

	prompt_set = lxml.etree.SubElement(match_interaction, "simpleMatchSet")
	for idx, prompt_text in enumerate(prompts_list, start=1):
		prompt_choice = lxml.etree.SubElement(prompt_set, "simpleAssociableChoice", {
			"identifier": f"prompt_{idx:03d}",
			"fixed": "true",
			"matchMax": "1",
			"matchMin": "0",
		})
		parsed_prompt = lxml.html.fragment_fromstring(html.unescape(prompt_text), create_parent='p')
		prompt_choice.append(parsed_prompt)

	choice_set = lxml.etree.SubElement(match_interaction, "simpleMatchSet")
	for idx, choice_text in enumerate(choices_list, start=1):
		assoc_choice = lxml.etree.SubElement(choice_set, "simpleAssociableChoice", {
			"identifier": f"choice_{idx:03d}",
			"fixed": "true",
			"matchMax": f"{len(prompts_list):d}",
			"matchMin": "0",
		})
		parsed_choice = lxml.html.fragment_fromstring(html.unescape(choice_text), create_parent='p')
		assoc_choice.append(parsed_choice)

	return item_body

#==============
def create_outcome_declarations() -> list:
	"""
	Create a minimal list of <outcomeDeclaration> elements.

	Returns:
		list: A list of <outcomeDeclaration> elements.
	"""
	outcome_declare_tree = [
		lxml.etree.Element(
			"outcomeDeclaration",
			attrib={
				"baseType": "float",
				"cardinality": "single",
				"identifier": "SCORE",
			},
		)
	]
	return outcome_declare_tree

#==============
def create_outcome_declarations_big() -> list:
	"""
	Create a list of <outcomeDeclaration> elements for SCORE, FEEDBACKBASIC, and MAXSCORE.

	Returns:
		list: A list of <outcomeDeclaration> elements.
	"""
	outcome_declare_tree = []

	# SCORE outcome declaration (Default Value = 0)
	score_declaration = lxml.etree.Element("outcomeDeclaration", {
		"baseType": "float",
		"cardinality": "single",
		"identifier": "SCORE",
	})
	default_value = lxml.etree.SubElement(score_declaration, "defaultValue")
	lxml.etree.SubElement(default_value, "value").text = "0"
	outcome_declare_tree.append(score_declaration)

	# FEEDBACKBASIC outcome declaration (No default value needed)
	feedback_declaration = lxml.etree.Element("outcomeDeclaration", {
		"baseType": "identifier",
		"cardinality": "single",
		"identifier": "FEEDBACKBASIC",
	})
	outcome_declare_tree.append(feedback_declaration)

	# MAXSCORE outcome declaration (Default Value = 0)
	maxscore_declaration = lxml.etree.Element("outcomeDeclaration", {
		"baseType": "float",
		"cardinality": "single",
		"identifier": "MAXSCORE",
	})
	default_value_max = lxml.etree.SubElement(maxscore_declaration, "defaultValue")
	lxml.etree.SubElement(default_value_max, "value").text = "0"
	outcome_declare_tree.append(maxscore_declaration)

	return outcome_declare_tree

#==============
def create_response_processing() -> lxml.etree.Element:
	"""
	Create a minimal <responseProcessing> element compatible with Canvas and Blackboard.

	Args:
		response_id (str): Identifier for the response.

	Returns:
		lxml.etree.Element: The minimal <responseProcessing> element.
	"""
	response_processing = lxml.etree.Element("responseProcessing")
	response_condition = lxml.etree.SubElement(response_processing, "responseCondition")
	response_if = lxml.etree.SubElement(response_condition, "responseIf")

	# Match correct response
	match = lxml.etree.SubElement(response_if, "match")
	lxml.etree.SubElement(match, "variable", {"identifier": "RESPONSE"})
	lxml.etree.SubElement(match, "correct", {"identifier": "RESPONSE"})

	return response_processing

#==============
def create_response_processing_MATCH() -> lxml.etree.Element:
	"""
	Create a <responseProcessing> element using the standard match template.
	"""
	return lxml.etree.Element("responseProcessing", {
		"template": "http://www.imsglobal.org/question/qti_v2p1/rptemplates/map_response"
	})

#==============
def create_response_declaration_ORDER(ordered_answers_list: list) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for ordering interactions.
	"""
	response_declaration = lxml.etree.Element(
		"responseDeclaration",
		attrib={
			"baseType": "identifier",
			"cardinality": "ordered",
			"identifier": "RESPONSE",
		},
	)
	correct_response = lxml.etree.SubElement(response_declaration, "correctResponse")
	for idx in range(len(ordered_answers_list)):
		choice_id = f"choice_{idx+1:03d}"
		lxml.etree.SubElement(correct_response, "value").text = choice_id
	return response_declaration

#==============
def create_item_body_ORDER(
		question_html_text: str, ordered_answers_list: list, shuffle: bool=True
		) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for an ordering interaction.
	"""
	item_body = lxml.etree.Element("itemBody")

	unescaped_text = html.unescape(question_html_text)
	parsed_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='div')
	item_body.append(parsed_html)

	order_interaction = lxml.etree.SubElement(item_body, "orderInteraction", {
		"responseIdentifier": "RESPONSE",
		"shuffle": str(shuffle).lower(),
	})
	prompt = lxml.etree.SubElement(order_interaction, "prompt")
	prompt.text = html.unescape(question_html_text)

	for idx, choice_text in enumerate(ordered_answers_list, start=1):
		simple_choice = lxml.etree.SubElement(order_interaction, "simpleChoice", {
			"identifier": f"choice_{idx:03d}",
		})
		parsed_choice = lxml.html.fragment_fromstring(html.unescape(choice_text), create_parent='p')
		simple_choice.append(parsed_choice)

	return item_body

#==============
def create_response_processing_ORDER() -> lxml.etree.Element:
	"""
	Create a <responseProcessing> element using the standard match_correct template.
	"""
	return lxml.etree.Element("responseProcessing", {
		"template": "http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"
	})

#==============
def create_response_declarations_MULTI_FIB(answer_map: dict) -> list:
	"""
	Create a list of <responseDeclaration> elements for each blank in MULTI_FIB.
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

#==============
def create_item_body_MULTI_FIB(question_html_text: str, answer_map: dict) -> lxml.etree.Element:
	"""
	Create <itemBody> for MULTI_FIB, replacing [key] markers with textEntryInteraction.
	"""
	item_body = lxml.etree.Element("itemBody")

	unescaped_text = html.unescape(question_html_text)
	for key in sorted(answer_map.keys()):
		placeholder = f"[{key}]"
		interaction = f'<textEntryInteraction responseIdentifier="{key}"></textEntryInteraction>'
		unescaped_text = unescaped_text.replace(placeholder, interaction)

	parsed_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='div')
	item_body.append(parsed_html)
	return item_body

#==============
def create_response_processing_MULTI_FIB(answer_map: dict) -> lxml.etree.Element:
	"""
	Create <responseProcessing> awarding partial credit per correct blank.
	"""
	response_processing = lxml.etree.Element("responseProcessing")
	blanks = list(sorted(answer_map.keys()))
	base_score = 100 / len(blanks) if blanks else 0

	for key in blanks:
		resp_condition = lxml.etree.SubElement(response_processing, "respcondition")
		conditionvar = lxml.etree.SubElement(resp_condition, "conditionvar")
		match = lxml.etree.SubElement(conditionvar, "match")
		lxml.etree.SubElement(match, "variable", {"identifier": key})
		lxml.etree.SubElement(match, "correct", {"identifier": key})
		setvar = lxml.etree.SubElement(resp_condition, "setvar", varname="SCORE", action="Add")
		setvar.text = f"{base_score:.2f}"

	return response_processing

#==============
def create_response_declaration_NUM(answer_float: float) -> lxml.etree.Element:
	"""
	Create a <responseDeclaration> for numeric entry.
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
	lxml.etree.SubElement(correct_response, "value").text = f"{answer_float}"
	return response_declaration

#==============
def create_item_body_NUM(question_html_text: str) -> lxml.etree.Element:
	"""
	Create the <itemBody> element for numeric entry using a textEntryInteraction.
	"""
	item_body = lxml.etree.Element("itemBody")

	unescaped_text = html.unescape(question_html_text)
	parsed_html = lxml.html.fragment_fromstring(unescaped_text, create_parent='div')
	item_body.append(parsed_html)

	text_entry_p = lxml.etree.SubElement(item_body, "p")
	lxml.etree.SubElement(text_entry_p, "textEntryInteraction", {
		"responseIdentifier": "RESPONSE"
	})
	return item_body

#==============
def create_response_processing_NUM(answer_float: float, tolerance_float: float,
		tolerance_mode: str="absolute",
		include_lower: bool=True, include_upper: bool=True) -> lxml.etree.Element:
	"""
	Create <responseProcessing> for numeric entry with tolerance support.
	"""
	response_processing = lxml.etree.Element("responseProcessing")
	resp_condition = lxml.etree.SubElement(response_processing, "responseCondition")
	resp_if = lxml.etree.SubElement(resp_condition, "responseIf")

	tolerance_str = f"{tolerance_float} {tolerance_float}"
	equal_attrs = {
		"toleranceMode": tolerance_mode,
		"tolerance": tolerance_str,
		"includeLowerBound": str(include_lower).lower(),
		"includeUpperBound": str(include_upper).lower(),
	}
	equal = lxml.etree.SubElement(resp_if, "equal", equal_attrs)
	lxml.etree.SubElement(equal, "variable", {"identifier": "RESPONSE"})
	lxml.etree.SubElement(equal, "correct", {"identifier": "RESPONSE"})

	set_outcome = lxml.etree.SubElement(resp_if, "setOutcomeValue", {"identifier": "SCORE"})
	lxml.etree.SubElement(set_outcome, "baseValue", {"baseType": "float"}).text = "100"

	resp_else = lxml.etree.SubElement(resp_condition, "responseElse")
	set_outcome_else = lxml.etree.SubElement(resp_else, "setOutcomeValue", {"identifier": "SCORE"})
	lxml.etree.SubElement(set_outcome_else, "baseValue", {"baseType": "float"}).text = "0"

	return response_processing

#==============
def create_response_processing_big() -> lxml.etree.Element:
	"""
	Create a <responseProcessing> element with correct feedback and scoring.
	"""
	# Create root <responseProcessing> element
	response_processing = lxml.etree.Element("responseProcessing")

	# Create <responseCondition>
	response_condition = lxml.etree.SubElement(response_processing, "responseCondition")

	# <responseIf> block for correct response
	response_if = lxml.etree.SubElement(response_condition, "responseIf")

	# Match correct response
	match = lxml.etree.SubElement(response_if, "match")
	lxml.etree.SubElement(match, "variable", identifier="RESPONSE")
	lxml.etree.SubElement(match, "correct", identifier="RESPONSE")

	# Assign MAXSCORE when correct
	set_outcome_score = lxml.etree.SubElement(response_if, "setOutcomeValue", identifier="SCORE")
	lxml.etree.SubElement(set_outcome_score, "variable", identifier="MAXSCORE")

	# Set correct feedback value
	set_feedback_correct = lxml.etree.SubElement(response_if, "setOutcomeValue", identifier="FEEDBACKBASIC")
	lxml.etree.SubElement(set_feedback_correct, "baseValue", baseType="identifier").text = "correct_fb"

	# <responseElse> block for incorrect response
	response_else = lxml.etree.SubElement(response_condition, "responseElse")

	# Set incorrect feedback value
	set_feedback_incorrect = lxml.etree.SubElement(response_else, "setOutcomeValue", identifier="FEEDBACKBASIC")
	lxml.etree.SubElement(set_feedback_incorrect, "baseValue", baseType="identifier").text = "incorrect_fb"

	return response_processing
