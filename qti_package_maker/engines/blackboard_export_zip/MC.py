"""
Blackboard pool `<item>` builder for single-answer Multiple Choice questions.

Builds the QTI-1.2-derived Blackboard pool subtree for one MC item. Shared XML
primitives and the per-item skeleton live in `common_xml`; this module adds only
MC's choice render block and its `title="correct"` scoring branch.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
def build_MC(item: item_types.MC) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a single-answer Multiple Choice question.

	Structure: `response_lid` (Single) + `render_choice` with one `response_label`
	per choice; resprocessing has a `title="correct"` branch keyed to the correct
	label ident, the standard `incorrect` branch, and one per-choice feedback
	branch per the samples.

	Args:
		item: An `item_types.MC` instance.

	Returns:
		The `<item>` element.
	"""
	# The response_lid ident is the literal "response" so the varequal
	# respident="response" emitted by the correct branch resolves on import,
	# matching the real Blackboard samples (NUM/FIB/MULTI_FIB do the same).
	response_ident = "response"
	# Per-choice label idents stay deterministic, matching the unique label
	# idents in the real samples.
	label_idents = [
		common_xml.make_ident(item.item_crc16, "label", index)
		for index in range(len(item.choices_list))
	]
	correct_index = item.choices_list.index(item.answer_text)
	correct_ident = label_idents[correct_index]

	item_el, _outer_flow, response_block = common_xml.build_item_skeleton(
		"Multiple Choice", 1, item.question_text
	)
	response_lid = build_choice_response_lid(
		response_ident, "Single", label_idents, item.choices_list
	)
	response_block.append(response_lid)

	# Resprocessing: correct branch + incorrect + per-choice feedback branches.
	resprocessing = common_xml.start_resprocessing(item_el, 1.0)
	resprocessing.append(_build_choice_correct_respcondition([correct_ident]))
	resprocessing.append(common_xml.build_incorrect_respcondition())
	for label_ident in label_idents:
		resprocessing.append(_build_per_choice_feedback(label_ident))

	for feedback in common_xml.build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

#============================================
def build_choice_response_lid(
	response_ident: str,
	cardinality: str,
	label_idents: list[str],
	choices_list: list[str],
) -> lxml.etree.Element:
	"""
	Build a `<response_lid>` with a `<render_choice>` of `<response_label>` choices.

	Shared by MC (cardinality "Single") and MA (cardinality "Multiple"); MA imports
	this builder so the choice render block stays identical between the two types.

	Args:
		response_ident: The response_lid identifier.
		cardinality: "Single" for MC, "Multiple" for MA.
		label_idents: One 32-hex ident per choice.
		choices_list: The choice HTML strings.

	Returns:
		The `<response_lid>` element.
	"""
	response_lid = lxml.etree.Element("response_lid", ident=response_ident)
	response_lid.set("rcardinality", cardinality)
	response_lid.set("rtiming", "No")
	render_choice = lxml.etree.SubElement(response_lid, "render_choice")
	render_choice.set("shuffle", "No")
	render_choice.set("minnumber", "0")
	render_choice.set("maxnumber", "0")
	# One labeled choice per option, text carried as SMART_TEXT.
	for label_ident, choice_html in zip(label_idents, choices_list):
		render_choice.append(common_xml.build_response_label(label_ident, choice_html))
	return response_lid

#============================================
def _build_choice_correct_respcondition(correct_idents: list[str]) -> lxml.etree.Element:
	"""
	Build the `<respcondition title="correct">` branch for MC.

	Args:
		correct_idents: The label idents that score as correct.

	Returns:
		The `<respcondition title="correct">` element.
	"""
	respcondition = lxml.etree.Element("respcondition", title="correct")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	# One varequal per correct choice (MC carries exactly one).
	for correct_ident in correct_idents:
		conditionvar.append(common_xml._varequal("response", correct_ident))
	common_xml.build_correct_setvar_and_feedback(respcondition)
	return respcondition

#============================================
def _build_per_choice_feedback(label_ident: str) -> lxml.etree.Element:
	"""
	Build a per-choice feedback `<respcondition>` (empty varequal, SCORE 0).

	The samples emit one such branch per choice so each choice can carry its own
	feedback hook; it sets SCORE to 0 and links feedback by the choice ident.

	Args:
		label_ident: The choice label ident.

	Returns:
		The `<respcondition>` element.
	"""
	respcondition = lxml.etree.Element("respcondition")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	# Empty-valued varequal keyed to the choice ident, matching the samples.
	conditionvar.append(common_xml._varequal(label_ident, None))
	setvar = lxml.etree.SubElement(respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "0"
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", label_ident)
	displayfeedback.set("feedbacktype", "Response")
	return respcondition
