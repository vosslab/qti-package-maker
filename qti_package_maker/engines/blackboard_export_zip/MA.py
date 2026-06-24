"""
Blackboard pool `<item>` builder for Multiple Answer questions.

Builds the QTI-1.2-derived Blackboard pool subtree for one MA item. The choice
render block is shared with MC (via `MC.build_choice_response_lid`); this module
adds MA's real-Blackboard `title="correct"` `<and>` branch and the per-choice
penalty branches Ultra needs to display correct answers and score.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import MC
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
def build_MA(item: item_types.MA) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Multiple Answer question.

	Structure mirrors MC but the `response_lid` uses `rcardinality="Multiple"`
	and the correct branch lists every choice in one `<and>` (correct choices as
	bare `<varequal respident="response">`, incorrect choices under `<not>`),
	followed by one per-choice penalty branch per choice. This is the real
	Blackboard MA scoring shape Ultra needs to display correct answers and score.

	Args:
		item: An `item_types.MA` instance.

	Returns:
		The `<item>` element.
	"""
	# The response_lid ident is the literal "response" so the varequal
	# respident="response" emitted by the correct branch resolves on import,
	# matching the real Blackboard samples.
	response_ident = "response"
	label_idents = [
		common_xml.make_ident(item.item_crc16, "label", index)
		for index in range(len(item.choices_list))
	]
	# Map each correct answer text to its choice label ident.
	correct_idents = [
		label_idents[item.choices_list.index(answer_text)]
		for answer_text in item.answers_list
	]

	item_el, _outer_flow, response_block = common_xml.build_item_skeleton(
		"Multiple Answer", 1, item.question_text
	)
	# Multiple cardinality lets the student select more than one choice.
	response_lid = MC.build_choice_response_lid(
		response_ident, "Multiple", label_idents, item.choices_list
	)
	response_block.append(response_lid)

	resprocessing = common_xml.start_resprocessing(item_el, 1.0)
	# Correct branch: one <and> over EVERY choice in order (correct bare, incorrect
	# under <not>), matching the real Blackboard MA shape so the item scores on Ultra.
	resprocessing.append(_build_ma_correct_respcondition(label_idents, correct_idents))
	resprocessing.append(common_xml.build_incorrect_respcondition())
	# One penalty branch per choice (count equals choice count), in choice order.
	for label_ident in label_idents:
		resprocessing.append(_build_ma_penalty_respcondition(label_ident))

	for feedback in common_xml.build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

#============================================
def _build_ma_correct_respcondition(
	label_idents: list[str],
	correct_idents: list[str],
) -> lxml.etree.Element:
	"""
	Build the real-Blackboard MA `<respcondition title="correct">` branch.

	The MA correct branch differs from MC: its `<conditionvar>` holds one `<and>`
	that lists EVERY choice in original choice order, not just the correct ones.
	Each correct choice is a bare `<varequal respident="response" case="No">IDENT</varequal>`;
	each incorrect choice is the same varequal wrapped in `<not>`. The trailing
	`setvar SCORE.max` + `displayfeedback linkrefid="correct"` pair is shared with MC.
	This is the exact shape Blackboard Ultra needs to display correct answers and
	score; the prior bare-varequal shape did not score (it left max-select at all
	options with no correct answer recorded).

	Args:
		label_idents: The choice label idents, in original choice order.
		correct_idents: The subset of label_idents that score as correct.

	Returns:
		The `<respcondition title="correct">` element.
	"""
	# Set membership for an O(1) correct/incorrect test while iterating in order.
	correct_ident_set = set(correct_idents)
	respcondition = lxml.etree.Element("respcondition", title="correct")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	and_el = lxml.etree.SubElement(conditionvar, "and")
	# Every choice appears once, in choice order: correct bare, incorrect under <not>.
	for label_ident in label_idents:
		choice_varequal = common_xml._varequal("response", label_ident)
		if label_ident in correct_ident_set:
			and_el.append(choice_varequal)
		else:
			and_el.append(common_xml._not(choice_varequal))
	common_xml.build_correct_setvar_and_feedback(respcondition)
	return respcondition

#============================================
def _build_ma_penalty_respcondition(label_ident: str) -> lxml.etree.Element:
	"""
	Build one real-Blackboard MA per-choice penalty `<respcondition>` (SCORE 0).

	The real MA samples emit one penalty branch per choice (count equals the
	choice count, not the incorrect count). Each branch holds an empty
	`<varequal respident="CHOICE_IDENT" case="No"/>` keyed to that choice's
	label ident and sets SCORE to 0; unlike MC's per-choice feedback branch it
	carries no `<displayfeedback>`. The label ident used here as `respident` is
	the SAME ident that appears as the TEXT of a `<varequal respident="response">`
	inside the correct branch's `<and>`.

	Args:
		label_ident: The choice label ident this penalty branch keys on.

	Returns:
		The `<respcondition>` element.
	"""
	respcondition = lxml.etree.Element("respcondition")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	# Empty-valued varequal keyed to the choice ident, matching the real samples.
	conditionvar.append(common_xml._varequal(label_ident, None))
	setvar = lxml.etree.SubElement(respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "0"
	return respcondition
