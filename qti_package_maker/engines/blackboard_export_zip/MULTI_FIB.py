"""
Blackboard pool `<item>` builder for Fill in the Blank Plus (multi-blank) questions.

Builds the QTI-1.2-derived Blackboard pool subtree for one MULTI_FIB item. Shared
XML primitives and the per-item skeleton live in `common_xml`; this module adds one
text-entry field per blank and the `<and>`-of-`<or>` correct branch.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
def build_MULTI_FIB(item: item_types.MULTI_FIB) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Fill in the Blank Plus question.

	Structure: one `response_str ident="KEY"` per blank (keys are the answer_map
	keys); a `title="correct"` branch whose `<conditionvar><and>` holds one
	`<or>` per blank, each `<or>` carrying a `<varequal respident="KEY" case="No">`
	per accepted answer for that blank, and SCORE set to SCORE.max; plus the
	standard `incorrect` branch. `qmd_absolutescore_max` equals the blank count.
	Blank placeholders stay inline in the question HTML (no per-blank render_fib in
	the question text itself); the response fields live in the RESPONSE_BLOCK.

	Args:
		item: An `item_types.MULTI_FIB` instance.

	Returns:
		The `<item>` element.
	"""
	# Stable key order so idents/branches are reproducible across runs.
	blank_keys = sorted(item.answer_map.keys())
	blank_count = len(blank_keys)

	item_el, _outer_flow, response_block = common_xml.build_item_skeleton(
		"Fill in the Blank Plus", blank_count, item.question_text
	)
	# One text-entry field per blank, keyed by the blank label.
	for blank_key in blank_keys:
		response_str = lxml.etree.SubElement(response_block, "response_str", ident=blank_key)
		response_str.set("rcardinality", "Single")
		response_str.set("rtiming", "No")
		response_str.append(common_xml.build_render_fib("String"))

	resprocessing = common_xml.start_resprocessing(item_el, float(blank_count))
	# Correct branch: an <and> of one <or> per blank.
	correct_respcondition = lxml.etree.SubElement(resprocessing, "respcondition", title="correct")
	conditionvar = lxml.etree.SubElement(correct_respcondition, "conditionvar")
	and_el = lxml.etree.SubElement(conditionvar, "and")
	for blank_key in blank_keys:
		or_el = lxml.etree.SubElement(and_el, "or")
		# Each accepted answer for this blank is one varequal inside the <or>.
		for accepted_answer in item.answer_map[blank_key]:
			or_el.append(common_xml._varequal(blank_key, accepted_answer))
	setvar = lxml.etree.SubElement(correct_respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "SCORE.max"
	displayfeedback = lxml.etree.SubElement(correct_respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "correct")
	displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(common_xml.build_incorrect_respcondition())

	for feedback in common_xml.build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el
