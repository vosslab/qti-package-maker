"""
Blackboard pool `<item>` builder for Fill in the Blank questions.

Builds the QTI-1.2-derived Blackboard pool subtree for one FIB item. Shared XML
primitives and the per-item skeleton live in `common_xml`; this module adds FIB's
single text-entry field, its per-answer scoring branches (no `<setvar>`, dual
`<displayfeedback>`), and the paired per-answer `<itemfeedback>` blocks.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
def build_FIB(item: item_types.FIB) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Fill in the Blank question.

	Structure: one `response_str ident="response"` + `render_fib fibtype="String"`;
	one `<respcondition title="<hex>">` per accepted answer with no `<setvar>` and
	two `<displayfeedback>` (one `linkrefid="correct"`, one `linkrefid="<hex>"` equal
	to the branch title); one incorrect branch with `<setvar>0`; the standard
	correct/incorrect `<itemfeedback>` pair; and one per-answer `<itemfeedback
	ident="<hex>">` with a `<solution>` wrapper. Real Blackboard shape confirmed from:
	BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch03a_Peptide_Side_Chain_2aa_FIB/res00002.dat
	BB_Export_ZIP/Pool_ExportFile_GC.202610_Ch02.4_Overhang_Sequence_FiB/res00002.dat

	Args:
		item: An `item_types.FIB` instance.

	Returns:
		The `<item>` element.
	"""
	item_el, _outer_flow, response_block = common_xml.build_item_skeleton(
		"Fill in the Blank", 1, item.question_text, item.item_crc16
	)
	# Single text-entry field keyed "response".
	response_str = lxml.etree.SubElement(response_block, "response_str", ident="response")
	response_str.set("rcardinality", "Single")
	response_str.set("rtiming", "No")
	response_str.append(common_xml.build_render_fib("String"))

	resprocessing = common_xml.start_resprocessing(item_el, 1.0)
	# One scoring branch per accepted answer. Real BB FIB omits <setvar> on these
	# branches and instead emits two <displayfeedback>: the first linkrefid="correct",
	# the second keyed to the branch's own hex title ident. Confirmed from:
	# BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch03a_Peptide_Side_Chain_2aa_FIB/res00002.dat
	# BB_Export_ZIP/Pool_ExportFile_GC.202610_Ch02.4_Overhang_Sequence_FiB/res00002.dat
	answer_title_idents = []
	for index, accepted_answer in enumerate(item.answers_list):
		title = common_xml.make_ident(item.item_crc16, "fib_answer", index)
		answer_title_idents.append(title)
		respcondition = lxml.etree.SubElement(resprocessing, "respcondition", title=title)
		conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
		conditionvar.append(common_xml._varequal("response", accepted_answer))
		# First displayfeedback: always links to the shared "correct" block.
		displayfeedback_correct = lxml.etree.SubElement(respcondition, "displayfeedback")
		displayfeedback_correct.set("linkrefid", "correct")
		displayfeedback_correct.set("feedbacktype", "Response")
		# Second displayfeedback: links to this answer's own hex ident (= title).
		displayfeedback_answer = lxml.etree.SubElement(respcondition, "displayfeedback")
		displayfeedback_answer.set("linkrefid", title)
		displayfeedback_answer.set("feedbacktype", "Response")
	resprocessing.append(common_xml.build_incorrect_respcondition())

	# Standard correct/incorrect itemfeedback pair, then one per-answer itemfeedback
	# (solution block with empty solutionmaterial) for each accepted answer.
	for feedback in common_xml.build_simple_itemfeedback():
		item_el.append(feedback)
	for answer_ident in answer_title_idents:
		item_el.append(_build_fib_answer_itemfeedback(answer_ident))
	return item_el

#============================================
def _build_fib_answer_itemfeedback(answer_ident: str) -> lxml.etree.Element:
	"""
	Build the per-accepted-answer `<itemfeedback>` block for a FIB item.

	Real Blackboard FIB items carry one `<itemfeedback ident="<hex>">` per
	accepted answer (in addition to the standard correct/incorrect pair).
	Each per-answer block wraps a `<solution>` with an empty
	`<solutionmaterial><flow_mat class="Block"/>`.

	Provenance: extracted from real pool
	BB_Export_ZIP/Pool_ExportFile_GC.202610_Ch02.4_Overhang_Sequence_FiB/res00002.dat
	(item 0, 3 accepted answers; each hex ident matches its respcondition title).
	Also confirmed for single-answer items in
	BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch03a_Peptide_Side_Chain_2aa_FIB/res00002.dat.

	Args:
		answer_ident: The hex title ident of the per-answer respcondition this
			feedback block is paired with.

	Returns:
		The `<itemfeedback>` element.
	"""
	itemfeedback = lxml.etree.Element("itemfeedback", ident=answer_ident, view="All")
	solution = lxml.etree.SubElement(itemfeedback, "solution")
	solution.set("view", "All")
	solution.set("feedbackstyle", "Complete")
	solutionmaterial = lxml.etree.SubElement(solution, "solutionmaterial")
	flow_mat = lxml.etree.SubElement(solutionmaterial, "flow_mat")
	flow_mat.set("class", "Block")
	return itemfeedback
