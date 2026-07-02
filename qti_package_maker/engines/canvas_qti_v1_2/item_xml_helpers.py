# Standard Library
#import html
#import random

# PIP3 modules
import lxml.etree

#==============================================================
def create_assessment_items_file_xml_header() -> lxml.etree.Element:
	""" Create the root <questestinterop> element with common namespaces and attributes. """
	nsmap = {
		None: "http://www.imsglobal.org/xsd/ims_qtiasiv1p2",
		"xsi": "http://www.w3.org/2001/XMLSchema-instance",
	}

	# Create the root element <questestinterop>
	assessment_items_file_xml_root = lxml.etree.Element(
		"questestinterop",
		nsmap=nsmap,
		attrib={
			"{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
				"http://www.imsglobal.org/xsd/ims_qtiasiv1p2 "
				"http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd"
			),
		},
	)
	return assessment_items_file_xml_root

#==============================================================
def create_itemmetadata(choice_ids_list: list, question_type: str) -> lxml.etree.Element:
	"""Create the <itemmetadata> section with QTI metadata fields."""
	itemmetadata = lxml.etree.Element("itemmetadata")
	qtimetadata = lxml.etree.SubElement(itemmetadata, "qtimetadata")

	# Define QTI metadata fields
	metadata_fields = [
		("question_type", question_type),
		("points_possible", "1.0"),
		("original_answer_ids", ','.join(choice_ids_list))
	]

	for field_label, field_entry in metadata_fields:
		field = lxml.etree.SubElement(qtimetadata, "qtimetadatafield")
		lxml.etree.SubElement(field, "fieldlabel").text = field_label
		lxml.etree.SubElement(field, "fieldentry").text = field_entry

	return itemmetadata

#==============================================================
def create_material_mattext(question_text: str) -> lxml.etree.Element:
	"""Create the <material> section inside <presentation>."""
	material = lxml.etree.Element("material")
	mattext = lxml.etree.SubElement(material, "mattext", texttype="text/html")
	# Question text in HTML format
	mattext.text = question_text
	return material

#==============================================================
def create_choice_response_lid(choices_list: list, cardinality: str="Single") -> lxml.etree.Element:
	"""Create the <response_lid> section with <render_choice> and answer options."""
	response_lid = lxml.etree.Element("response_lid", ident="response1", rcardinality=cardinality)
	render_choice = lxml.etree.SubElement(response_lid, "render_choice")

	# Create choices
	for index, choice_text in enumerate(choices_list, start=1):
		choice_id = f"choice_{index:03d}"
		response_label = lxml.etree.SubElement(render_choice, "response_label", ident=choice_id)
		material = lxml.etree.SubElement(response_label, "material")
		mattext = lxml.etree.SubElement(material, "mattext", texttype="text/html")
		mattext.text = choice_text  # Set choice text
	return response_lid

#==============================================================
def create_matching_response_lid(prompts_list: list, choices_list: list) -> list[lxml.etree.Element]:
	"""Create the <response_lid> sections for matching questions."""
	response_lids = []
	# Iterate through answers and create a <response_lid> for each one
	for i, prompt_text in enumerate(prompts_list):
		response_lid = lxml.etree.Element("response_lid", ident=f"response_{i+1:03d}")
		#response_lid = lxml.etree.Element("response_lid", ident=f"prompt{i + 1}")

		# Add the main item (left-side term)
		material = lxml.etree.SubElement(response_lid, "material")
		mattext = lxml.etree.SubElement(material, "mattext", texttype="text/html")
		mattext.text = prompt_text  # Example: "orange", "banana", "lettuce"

		# Create <render_choice> section for match options
		render_choice = lxml.etree.SubElement(response_lid, "render_choice")

		# Add each matching choice as a response_label
		for j, choice_text in enumerate(choices_list):
			response_label = lxml.etree.SubElement(render_choice, "response_label", ident=f"choice_{j+1:03d}")
			label_material = lxml.etree.SubElement(response_label, "material")
			label_mattext = lxml.etree.SubElement(label_material, "mattext")
			label_mattext.text = choice_text  # Example: "orange", "yellow", "green", "distractor"

		response_lids.append(response_lid)

	return response_lids

#==============================================================
def _create_base_outcomes() -> lxml.etree.Element:
	"""
	Create the base <resprocessing> structure with <outcomes> and <decvar>.

	Returns:
		lxml.etree.Element: The <resprocessing> XML element.
	"""
	resprocessing = lxml.etree.Element("resprocessing")

	# Define outcomes (scoring)
	outcomes = lxml.etree.SubElement(resprocessing, "outcomes")
	lxml.etree.SubElement(outcomes, "decvar", maxvalue="100", minvalue="0", varname="SCORE", vartype="Decimal")

	return resprocessing

#==============================================================
def create_MC_resprocessing(choices_list: list, answer_text: str) -> lxml.etree.Element:
	"""
	Create the <resprocessing> section for Multiple Choice (Single Answer) questions.
	"""
	# Get the base <resprocessing>
	resprocessing = _create_base_outcomes()

	# Define response condition
	respcondition = lxml.etree.SubElement(resprocessing, "respcondition")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")

	# Multiple Choice (Single) -> NO `<and>`, NO `<not>`, just a single `<varequal>`
	correct_choice_id = f"choice_{choices_list.index(answer_text)+1:03d}"
	lxml.etree.SubElement(conditionvar, "varequal", respident="response1").text = correct_choice_id

	# Assign full 100 points only if the condition is met
	lxml.etree.SubElement(respcondition, "setvar", action="Set", varname="SCORE").text = "100"

	return resprocessing

#==============================================================
def create_MA_resprocessing(choices_list: list, answers_list: list) -> lxml.etree.Element:
	"""
	Create the <resprocessing> section, automatically sorting correct and incorrect answers.
	"""
	# Get the base <resprocessing>
	resprocessing = _create_base_outcomes()

	# Define response condition
	respcondition = lxml.etree.SubElement(resprocessing, "respcondition")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	and_condition = lxml.etree.SubElement(conditionvar, "and")

	# Add correct answer conditions
	for i, choice_text in enumerate(choices_list):
		choice_id = f"choice_{i+1:03d}"
		if choice_text in answers_list:
			lxml.etree.SubElement(and_condition, "varequal", respident="response1").text = choice_id
		else:
			not_condition = lxml.etree.SubElement(and_condition, "not")
			lxml.etree.SubElement(not_condition, "varequal", respident="response1").text = choice_id

	# Assign full 100 points only if the condition is met
	lxml.etree.SubElement(respcondition, "setvar", action="Set", varname="SCORE").text = "100"

	return resprocessing

#==============================================================
def create_MATCH_resprocessing(prompts_list: list) -> lxml.etree.Element:
	"""
	Create the <resprocessing> section for matching questions, assigning scores for each match.
	"""
	# Get the base <resprocessing>
	resprocessing = _create_base_outcomes()

	# Distribute points evenly
	base_score = round(100 / len(prompts_list), 2)

	# Create conditions for each correct match
	for i in range(len(prompts_list)):
		respcondition = lxml.etree.SubElement(resprocessing, "respcondition")
		conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")

		# Match the correct response
		lxml.etree.SubElement(conditionvar, "varequal", respident=f"response_{i+1:03d}").text = f"choice_{i+1:03d}"
		#lxml.etree.SubElement(conditionvar, "varequal", respident=f"prompt{i + 1}").text = f"choice_{i + 1}"

		# Assign a portion of the score
		lxml.etree.SubElement(respcondition, "setvar", varname="SCORE", action="Add").text = f"{base_score:.2f}"

	return resprocessing

#==============================================================
def create_numeric_presentation(question_text: str) -> lxml.etree.Element:
	"""
	Create <presentation> for a numeric response (fill-in) using response_str.
	"""
	presentation = lxml.etree.Element("presentation")
	material_mattext = create_material_mattext(question_text)
	presentation.append(material_mattext)

	response_str = lxml.etree.SubElement(presentation, "response_str", ident="response1", rcardinality="Single")
	render_fib = lxml.etree.SubElement(response_str, "render_fib", fibtype="Decimal")
	lxml.etree.SubElement(render_fib, "response_label", ident="answer1", rshuffle="No")
	return presentation

#==============================================================
def create_NUM_resprocessing(answer_float: float, tolerance_float: float | None) -> lxml.etree.Element:
	"""
	Create <resprocessing> for numeric questions with optional tolerance.
	"""
	resprocessing = _create_base_outcomes()
	respcondition = lxml.etree.SubElement(resprocessing, "respcondition", **{"continue": "No"})
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")

	if tolerance_float is None:
		varequal = lxml.etree.SubElement(conditionvar, "varequal", respident="response1")
		varequal.text = f"{answer_float}"
	else:
		or_block = lxml.etree.SubElement(conditionvar, "or")
		exact = lxml.etree.SubElement(or_block, "varequal", respident="response1")
		exact.text = f"{answer_float}"
		and_block = lxml.etree.SubElement(or_block, "and")
		lower = lxml.etree.SubElement(and_block, "vargte", respident="response1")
		lower.text = f"{answer_float - tolerance_float}"
		upper = lxml.etree.SubElement(and_block, "varlte", respident="response1")
		upper.text = f"{answer_float + tolerance_float}"

	lxml.etree.SubElement(respcondition, "setvar", action="Set", varname="SCORE").text = "100"
	return resprocessing

#==============================================================
def create_fib_presentation(question_text: str) -> lxml.etree.Element:
	"""
	Create <presentation> for a single fill-in-the-blank string response.
	"""
	presentation = lxml.etree.Element("presentation")
	material_mattext = create_material_mattext(question_text)
	presentation.append(material_mattext)

	response_str = lxml.etree.SubElement(presentation, "response_str", ident="response1", rcardinality="Single")
	render_fib = lxml.etree.SubElement(response_str, "render_fib", fibtype="String")
	lxml.etree.SubElement(render_fib, "response_label", ident="answer1", rshuffle="No")
	return presentation

#==============================================================
def create_FIB_resprocessing(answers_list: list) -> lxml.etree.Element:
	"""
	Create <resprocessing> for fill-in-the-blank with optional multiple acceptable answers.
	"""
	resprocessing = _create_base_outcomes()
	respcondition = lxml.etree.SubElement(resprocessing, "respcondition", **{"continue": "No"})
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")

	for answer in answers_list:
		varequal = lxml.etree.SubElement(conditionvar, "varequal", respident="response1")
		varequal.text = answer

	lxml.etree.SubElement(respcondition, "setvar", action="Set", varname="SCORE").text = "100"
	return resprocessing

#==============================================================
def create_multi_fib_presentation(question_text: str, answer_map: dict) -> lxml.etree.Element:
	"""
	Create <presentation> for multiple fill-in-the-blank responses using response_lid.
	"""
	presentation = lxml.etree.Element("presentation")
	material_mattext = create_material_mattext(question_text)
	presentation.append(material_mattext)

	response_lids, _ = create_multi_fib_response_lids(answer_map)
	for rl in response_lids:
		presentation.append(rl)
	return presentation

#==============================================================
def create_multi_fib_response_lids(answer_map: dict) -> tuple[list[lxml.etree.Element], list[str]]:
	"""
	Create response_lid blocks for each blank with choices for acceptable answers.
	Returns (response_lids, label_ids_list).
	"""
	response_lids = []
	label_ids = []
	for idx, key in enumerate(sorted(answer_map.keys()), start=1):
		respident = f"response_{idx}"
		response_lid = lxml.etree.Element("response_lid", ident=respident)

		material = lxml.etree.SubElement(response_lid, "material")
		lxml.etree.SubElement(material, "mattext").text = str(key)

		render_choice = lxml.etree.SubElement(response_lid, "render_choice")
		for choice_idx, answer in enumerate(answer_map[key], start=1):
			label_id = f"{respident}_choice_{choice_idx:03d}"
			label_ids.append(label_id)
			response_label = lxml.etree.SubElement(render_choice, "response_label", ident=label_id)
			mat = lxml.etree.SubElement(response_label, "material")
			lxml.etree.SubElement(mat, "mattext", texttype="text/plain").text = answer

		response_lids.append(response_lid)
	return response_lids, label_ids

#==============================================================
def create_MULTI_FIB_resprocessing(answer_map: dict) -> lxml.etree.Element:
	"""
	Create <resprocessing> for multi-blank FIB with all blanks required.
	"""
	resprocessing = _create_base_outcomes()
	blanks = list(sorted(answer_map.keys()))
	base_score = round(100 / len(blanks), 2) if blanks else 0

	for idx, key in enumerate(blanks, start=1):
		respident = f"response_{idx}"
		answers_list = answer_map[key]
		respcondition = lxml.etree.SubElement(resprocessing, "respcondition")
		conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
		if len(answers_list) == 1:
			v = lxml.etree.SubElement(conditionvar, "varequal", respident=respident)
			v.text = answers_list[0]
		else:
			or_block = lxml.etree.SubElement(conditionvar, "or")
			for answer in answers_list:
				v = lxml.etree.SubElement(or_block, "varequal", respident=respident)
				v.text = answer
		lxml.etree.SubElement(respcondition, "setvar", varname="SCORE", action="Add").text = f"{base_score:.2f}"
	return resprocessing

#==============================================================
#==============================================================
def dummy_test_run() -> None:
	"""
	Run a test generation of assessment XML.
	"""
	assessment_xml = create_assessment_items_file_xml_header(
		assessment_id="qti12_questions",
		assessment_title="minimal_qti_1.2_sample",
		section_id="root_section"
	)

	# Pretty print XML
	assessment_xml_string = lxml.etree.tostring(
		assessment_xml, pretty_print=True, xml_declaration=True, encoding="UTF-8"
	)

	# Save to file
	with open("assessment.xml", "w", encoding="utf-8") as f:
		f.write(assessment_xml_string.decode("utf-8"))

#==============
if __name__ == "__main__":
	dummy_test_run()
