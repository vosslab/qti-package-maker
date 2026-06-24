"""
Blackboard pool `<item>` builder for Matching questions.

Builds the QTI-1.2-derived Blackboard pool subtree for one MATCH item. Shared XML
primitives and the per-item skeleton live in `common_xml`; this module adds the
per-prompt `response_lid` flows inside RESPONSE_BLOCK, the sibling RIGHT_MATCH_BLOCK
holding the choice texts, and one scoring branch per prompt.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
def build_MATCH(item: item_types.MATCH) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Matching question.

	Structure mirrors the real sample: each prompt is a `<flow class="Block">`
	holding a `response_lid` (whose `render_choice` lists one `response_label` per
	right-side choice, idents unique per prompt) followed by the prompt's
	FORMATTED_TEXT_BLOCK. A sibling `<flow class="RIGHT_MATCH_BLOCK">` holds the
	choice texts in order. resprocessing has one `<respcondition>` per prompt
	(`varequal respident="PROMPT_LID">CORRECT_LABEL_IDENT`) plus the incorrect
	branch.

	The pairing convention (so the reader can recover it): for prompt index i, the
	correct choice is choices_list[i], and that choice's positional label ident in
	prompt i's render_choice is the varequal value. The reader maps the correct
	label ident back to its position in the prompt's label list, then indexes
	RIGHT_MATCH_BLOCK by that position to recover the choice text.

	Args:
		item: An `item_types.MATCH` instance.

	Returns:
		The `<item>` element.
	"""
	prompts = item.prompts_list
	choices = item.choices_list

	item_el, outer_flow, response_block = common_xml.build_item_skeleton(
		"Matching", 1, item.question_text
	)

	# Track each prompt's correct-label ident for the resprocessing branches.
	prompt_response_idents = []
	correct_label_idents = []
	for prompt_index, prompt_html in enumerate(prompts):
		prompt_response_ident = common_xml.make_ident(item.item_crc16, "match_prompt", prompt_index)
		prompt_response_idents.append(prompt_response_ident)
		# One label ident per choice, unique to this prompt and positional.
		prompt_label_idents = [
			common_xml.make_ident(item.item_crc16, f"match_label_{prompt_index}", choice_index)
			for choice_index in range(len(choices))
		]
		# Pairing convention: prompt i pairs with choices[i] -> label at position i.
		correct_label_idents.append(prompt_label_idents[prompt_index])

		prompt_flow = lxml.etree.SubElement(response_block, "flow")
		prompt_flow.set("class", "Block")
		response_lid = lxml.etree.SubElement(prompt_flow, "response_lid", ident=prompt_response_ident)
		response_lid.set("rcardinality", "Single")
		response_lid.set("rtiming", "No")
		render_choice = lxml.etree.SubElement(response_lid, "render_choice")
		render_choice.set("shuffle", "Yes")
		render_choice.set("minnumber", "0")
		render_choice.set("maxnumber", "0")
		flow_label = lxml.etree.SubElement(render_choice, "flow_label")
		flow_label.set("class", "Block")
		# MATCH labels carry no inline text; choice text lives in RIGHT_MATCH_BLOCK.
		for prompt_label_ident in prompt_label_idents:
			inner_label = lxml.etree.SubElement(flow_label, "response_label")
			inner_label.set("ident", prompt_label_ident)
			inner_label.set("shuffle", "Yes")
			inner_label.set("rarea", "Ellipse")
			inner_label.set("rrange", "Exact")
		# The prompt's own display text follows its response_lid.
		prompt_flow.append(common_xml.build_formatted_text_flow(prompt_html))

	# Right-side choice texts, in choices_list order, indexed positionally.
	# RIGHT_MATCH_BLOCK is a sibling of RESPONSE_BLOCK (a child of outer_flow),
	# matching the real Blackboard samples. Ultra fails to render the item if this
	# block is nested inside RESPONSE_BLOCK instead.
	right_match_block = lxml.etree.SubElement(outer_flow, "flow")
	right_match_block.set("class", "RIGHT_MATCH_BLOCK")
	for choice_html in choices:
		choice_flow = lxml.etree.SubElement(right_match_block, "flow")
		choice_flow.set("class", "Block")
		choice_flow.append(common_xml.build_formatted_text_flow(choice_html))

	resprocessing = common_xml.start_resprocessing(item_el, 1.0)
	# One scoring branch per prompt: prompt ident -> its correct label ident.
	for prompt_response_ident, correct_label_ident in zip(prompt_response_idents, correct_label_idents):
		respcondition = lxml.etree.SubElement(resprocessing, "respcondition")
		conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
		conditionvar.append(common_xml._varequal(prompt_response_ident, correct_label_ident))
		displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
		displayfeedback.set("linkrefid", "correct")
		displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(common_xml.build_incorrect_respcondition())

	for feedback in common_xml.build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el
