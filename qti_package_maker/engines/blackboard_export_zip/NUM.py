"""
Blackboard pool `<item>` builder for Numeric questions.

Builds the QTI-1.2-derived Blackboard pool subtree for one NUM item. Shared XML
primitives and the per-item skeleton live in `common_xml`; this module adds NUM's
numeric-entry field and its tolerance-window correct branch.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
def build_NUM(item: item_types.NUM) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Numeric question.

	Structure: `response_num ident="response"` + `render_fib fibtype="Decimal"`;
	a single correct `<respcondition>` holding `<vargte>` (answer - tolerance),
	`<varlte>` (answer + tolerance), and an exact `<varequal>`; plus the standard
	`incorrect` branch.

	Args:
		item: An `item_types.NUM` instance.

	Returns:
		The `<item>` element.
	"""
	# Tolerance window: lower = answer - tol, upper = answer + tol.
	lower_bound = item.answer_float - item.tolerance_float
	upper_bound = item.answer_float + item.tolerance_float

	item_el, _outer_flow, response_block = common_xml.build_item_skeleton(
		"Numeric", 1, item.question_text
	)
	# Numeric entry field keyed "response".
	response_num = lxml.etree.SubElement(response_block, "response_num", ident="response")
	response_num.set("rcardinality", "Single")
	response_num.set("rtiming", "No")
	response_num.append(common_xml.build_render_fib("Decimal"))

	resprocessing = common_xml.start_resprocessing(item_el, 1.0)
	# Correct branch: lower <= response <= upper, plus the exact value.
	correct_title = common_xml.make_ident(item.item_crc16, "num_correct", 0)
	respcondition = lxml.etree.SubElement(resprocessing, "respcondition", title=correct_title)
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	vargte = lxml.etree.SubElement(conditionvar, "vargte", respident="response")
	vargte.text = common_xml.format_number(lower_bound)
	varlte = lxml.etree.SubElement(conditionvar, "varlte", respident="response")
	varlte.text = common_xml.format_number(upper_bound)
	conditionvar.append(common_xml._varequal("response", common_xml.format_number(item.answer_float)))
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "correct")
	displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(common_xml.build_incorrect_respcondition())

	for feedback in common_xml.build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el
