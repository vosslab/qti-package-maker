"""
Per-item Blackboard pool XML builders (QTI-1.2-derived envelope + BB extensions).

This module builds the `<item>` subtree for each first-class assessment type in
Blackboard's proprietary pool-export dialect. The dialect reuses the QTI-1.2 ASI
envelope (`questestinterop`, `response_lid`, `render_choice`, `resprocessing`,
`varequal`) but the payload is Blackboard-specific: `bbmd_*` itemmetadata,
`mat_formattedtext type="SMART_TEXT"` HTML carriers, `flow class` block nesting,
and `RIGHT_MATCH_BLOCK` for matching.

Each public `build_<type>(item)` function takes an internal item instance from
`qti_package_maker.assessment_items.item_types` and returns an
`lxml.etree.Element` rooted at `<item>`. The write dispatcher calls one
function per supported type.

The schema here is shaped from byte-level study of real sample pools under
`BB_Export_ZIP/`; it is NOT QTI 2.1 and shares no builder with the QTI 2.1
engines. See `docs/active_plans/audits/blackboard_export_zip_forgeability.md`.
"""

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

#============================================
# Deterministic identifier generation
#============================================
# Blackboard samples use 32-character hex idents (UUIDs with dashes removed).
# We derive stable 32-char hex idents from item content so round-trip diffs and
# debugging stay reproducible. Each ident is eight CRC16 nib's-worth (8 * 4 = 32
# hex chars) computed from the item CRC16 plus a role tag and positional index.

# Number of CRC16 chunks to concatenate for a full-length (32 hex char) ident.
_IDENT_CHUNKS = 8

#============================================
def make_ident(item_crc16: str, role: str, index: int) -> str:
	"""
	Build a deterministic 32-character hex identifier from item content.

	Args:
		item_crc16: The item's CRC16 string (e.g. "1a2b_3c4d").
		role: A short role tag distinguishing ident families ("response_lid",
			"label", "prompt", etc.).
		index: A positional index within that role family.

	Returns:
		A 32-character lowercase hex string, shaped like a dashless UUID.
	"""
	# Collapse underscores so the seed is a clean token.
	crc_token = str(item_crc16).replace('_', '')
	chunks = []
	# Concatenate several salted CRC16 values to reach 32 hex characters.
	for chunk_index in range(_IDENT_CHUNKS):
		seed = f"{crc_token}|{role}|{index}|{chunk_index}"
		chunks.append(string_functions.get_crc16_from_string(seed))
	ident = "".join(chunks)
	return ident

#============================================
# Low-level element builders
#============================================
#============================================
def build_smart_text(html_payload: str) -> lxml.etree.Element:
	"""
	Build a `mat_formattedtext type="SMART_TEXT"` element carrying HTML markup.

	The HTML is assigned as the element TEXT so lxml entity-escapes it exactly
	once: input `K<sup>+</sup> & Cl` is serialized as
	`K&lt;sup&gt;+&lt;/sup&gt; &amp; Cl`. The read path reverses this by reading
	the element text back (un-escaped), recovering the original HTML. The inner
	HTML is carried verbatim, so anti-cheat spans and RDKit/script markup survive.

	Args:
		html_payload: The question/choice HTML string to carry.

	Returns:
		The `<mat_formattedtext>` element.
	"""
	mat_formattedtext = lxml.etree.Element("mat_formattedtext", type="SMART_TEXT")
	# Assigning to .text makes lxml escape the HTML once on serialization.
	mat_formattedtext.text = html_payload
	return mat_formattedtext

#============================================
def build_material_block(html_payload: str) -> lxml.etree.Element:
	"""
	Build a `<material><mat_extension><mat_formattedtext .../></mat_extension></material>` block.

	Args:
		html_payload: The HTML string to carry as SMART_TEXT.

	Returns:
		The `<material>` element wrapping the SMART_TEXT payload.
	"""
	material = lxml.etree.Element("material")
	mat_extension = lxml.etree.SubElement(material, "mat_extension")
	mat_extension.append(build_smart_text(html_payload))
	return material

#============================================
def build_formatted_text_flow(html_payload: str) -> lxml.etree.Element:
	"""
	Build a `<flow class="FORMATTED_TEXT_BLOCK">` wrapping a SMART_TEXT material block.

	Args:
		html_payload: The HTML string to carry.

	Returns:
		The `<flow class="FORMATTED_TEXT_BLOCK">` element.
	"""
	flow = lxml.etree.Element("flow")
	flow.set("class", "FORMATTED_TEXT_BLOCK")
	flow.append(build_material_block(html_payload))
	return flow

#============================================
def build_question_block(question_html: str) -> lxml.etree.Element:
	"""
	Build the `<flow class="QUESTION_BLOCK">` holding the question's formatted text.

	Args:
		question_html: The question text HTML.

	Returns:
		The `<flow class="QUESTION_BLOCK">` element.
	"""
	question_block = lxml.etree.Element("flow")
	question_block.set("class", "QUESTION_BLOCK")
	question_block.append(build_formatted_text_flow(question_html))
	return question_block

#============================================
def build_itemmetadata(question_type: str, absolutescore_max: int) -> lxml.etree.Element:
	"""
	Build the `<itemmetadata>` block with Blackboard `bbmd_*` / `qmd_*` fields.

	The field set mirrors the real sample pools: the `bbmd_questiontype` element
	value is the type marker the reader keys on, and `qmd_absolutescore_max` is
	the score weight (1 for single-point types, blank count for MULTI_FIB).

	Args:
		question_type: The `bbmd_questiontype` element value
			(e.g. "Multiple Choice", "Numeric").
		absolutescore_max: The maximum absolute score (1, or blank count).

	Returns:
		The `<itemmetadata>` element.
	"""
	itemmetadata = lxml.etree.Element("itemmetadata")
	# bbmd_asitype/assessmenttype mark this as a pool item, matching the samples.
	_add_text_child(itemmetadata, "bbmd_asitype", "Item")
	_add_text_child(itemmetadata, "bbmd_assessmenttype", "Pool")
	_add_text_child(itemmetadata, "bbmd_sectiontype", "Subsection")
	# The question-type marker the read path parses.
	_add_text_child(itemmetadata, "bbmd_questiontype", question_type)
	_add_text_child(itemmetadata, "bbmd_is_from_cartridge", "false")
	_add_text_child(itemmetadata, "bbmd_is_disabled", "false")
	_add_text_child(itemmetadata, "bbmd_negative_points_ind", "N")
	_add_text_child(itemmetadata, "bbmd_canvas_fullcrdt_ind", "false")
	_add_text_child(itemmetadata, "bbmd_all_fullcredit_ind", "false")
	_add_text_child(itemmetadata, "bbmd_numbertype", "none")
	# Empty elements present in the samples; kept for structural fidelity.
	lxml.etree.SubElement(itemmetadata, "bbmd_partialcredit")
	_add_text_child(itemmetadata, "bbmd_orientationtype", "vertical")
	_add_text_child(itemmetadata, "bbmd_is_extracredit", "false")
	lxml.etree.SubElement(itemmetadata, "bbmd_is_metadataenabled")
	_add_text_child(itemmetadata, "bbmd_ai_state", "No")
	# Score weighting: samples store a fixed 15-decimal-place float string.
	score_text = f"{absolutescore_max:.15f}"
	_add_text_child(itemmetadata, "qmd_absolutescore_max", score_text)
	_add_text_child(itemmetadata, "qmd_weighting", "0")
	lxml.etree.SubElement(itemmetadata, "qmd_instructornotes")
	return itemmetadata

#============================================
def _add_text_child(parent: lxml.etree.Element, tag: str, text: str) -> lxml.etree.Element:
	"""
	Append a child element with the given tag and text to a parent.

	Args:
		parent: The parent element.
		tag: The child element tag name.
		text: The text content for the child.

	Returns:
		The newly created child element.
	"""
	child = lxml.etree.SubElement(parent, tag)
	child.text = text
	return child

#============================================
def build_outcomes(max_score: float) -> lxml.etree.Element:
	"""
	Build the `<outcomes>` block declaring the SCORE variable.

	Args:
		max_score: The maximum score value used for `maxvalue`.

	Returns:
		The `<outcomes>` element holding a single `<decvar>`.
	"""
	outcomes = lxml.etree.Element("outcomes")
	decvar = lxml.etree.SubElement(outcomes, "decvar")
	decvar.set("varname", "SCORE")
	decvar.set("vartype", "Decimal")
	decvar.set("defaultval", "0")
	decvar.set("minvalue", "0")
	# Samples format maxvalue with five decimal places.
	decvar.set("maxvalue", f"{max_score:.5f}")
	return outcomes

#============================================
def build_incorrect_respcondition() -> lxml.etree.Element:
	"""
	Build the trailing `<respcondition title="incorrect">` branch.

	This `<other/>` branch sets SCORE to 0 for any non-matching response and is
	present in every sample type.

	Returns:
		The `<respcondition title="incorrect">` element.
	"""
	respcondition = lxml.etree.Element("respcondition", title="incorrect")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	lxml.etree.SubElement(conditionvar, "other")
	setvar = lxml.etree.SubElement(respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "0"
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "incorrect")
	displayfeedback.set("feedbacktype", "Response")
	return respcondition

#============================================
def build_simple_itemfeedback() -> list[lxml.etree.Element]:
	"""
	Build the standard pair of empty `<itemfeedback>` blocks (correct/incorrect).

	Returns:
		A list of two `<itemfeedback>` elements with empty flow_mat blocks.
	"""
	feedback_elements = []
	for ident in ("correct", "incorrect"):
		itemfeedback = lxml.etree.Element("itemfeedback", ident=ident, view="All")
		flow_mat = lxml.etree.SubElement(itemfeedback, "flow_mat")
		flow_mat.set("class", "Block")
		feedback_elements.append(itemfeedback)
	return feedback_elements

#============================================
def build_response_label(ident: str, choice_html: str | None) -> lxml.etree.Element:
	"""
	Build a `<flow_label class="Block">` wrapping a `<response_label>`.

	For MC/MA the response_label carries the choice text as a FORMATTED_TEXT_BLOCK.
	For MATCH the right-side text lives in RIGHT_MATCH_BLOCK, so `choice_html` is
	None and the response_label is self-closing.

	Args:
		ident: The 32-hex response_label identifier.
		choice_html: The choice HTML, or None for MATCH labels (no inline text).

	Returns:
		The `<flow_label class="Block">` element.
	"""
	flow_label = lxml.etree.Element("flow_label")
	flow_label.set("class", "Block")
	response_label = lxml.etree.SubElement(flow_label, "response_label")
	response_label.set("ident", ident)
	response_label.set("shuffle", "Yes")
	response_label.set("rarea", "Ellipse")
	response_label.set("rrange", "Exact")
	# MC/MA carry the choice text; MATCH labels stay empty (text in RIGHT_MATCH_BLOCK).
	if choice_html is not None:
		flow_mat = lxml.etree.SubElement(response_label, "flow_mat")
		flow_mat.set("class", "FORMATTED_TEXT_BLOCK")
		flow_mat.append(build_material_block(choice_html))
	return flow_label

#============================================
def build_render_fib(fibtype: str) -> lxml.etree.Element:
	"""
	Build a `<render_fib>` element for FIB/NUM/MULTI_FIB response fields.

	Args:
		fibtype: The fill-in-blank field type ("String" for text, "Decimal" for
			numeric).

	Returns:
		The `<render_fib>` element.
	"""
	render_fib = lxml.etree.Element("render_fib")
	render_fib.set("charset", "us-ascii")
	render_fib.set("encoding", "UTF_8")
	render_fib.set("rows", "0")
	render_fib.set("columns", "0")
	render_fib.set("maxchars", "0")
	render_fib.set("prompt", "Box")
	render_fib.set("fibtype", fibtype)
	render_fib.set("minnumber", "0")
	render_fib.set("maxnumber", "0")
	return render_fib

#============================================
def _new_item_element() -> lxml.etree.Element:
	"""
	Create the root `<item maxattempts="0">` element.

	Returns:
		The `<item>` element.
	"""
	item = lxml.etree.Element("item", maxattempts="0")
	return item

#============================================
def _varequal(respident: str, value: str | None, case_no: bool = True) -> lxml.etree.Element:
	"""
	Build a `<varequal>` condition element.

	Args:
		respident: The response identifier this condition tests.
		value: The expected value as element text, or None for an empty match.
		case_no: When True, sets `case="No"` (case-insensitive).

	Returns:
		The `<varequal>` element.
	"""
	varequal = lxml.etree.Element("varequal", respident=respident)
	if case_no:
		varequal.set("case", "No")
	if value is not None:
		varequal.text = value
	return varequal

#============================================
# Per-type item builders
#============================================
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
		make_ident(item.item_crc16, "label", index)
		for index in range(len(item.choices_list))
	]
	correct_index = item.choices_list.index(item.answer_text)
	correct_ident = label_idents[correct_index]

	item_el = _new_item_element()
	item_el.append(build_itemmetadata("Multiple Choice", 1))

	# Presentation: question block + a choice render block.
	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(item.question_text))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")
	response_lid = _build_choice_response_lid(
		response_ident, "Single", label_idents, item.choices_list
	)
	response_block.append(response_lid)

	# Resprocessing: correct branch + incorrect + per-choice feedback branches.
	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(1.0))
	resprocessing.append(
		_build_choice_correct_respcondition([correct_ident])
	)
	resprocessing.append(build_incorrect_respcondition())
	for label_ident in label_idents:
		resprocessing.append(_build_per_choice_feedback(label_ident))

	for feedback in build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

#============================================
def build_MA(item: item_types.MA) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Multiple Answer question.

	Structure mirrors MC but the `response_lid` uses `rcardinality="Multiple"`
	and the correct branch tests every correct label ident (additive scoring via
	one varequal per correct answer in the `title="correct"` branch).

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
		make_ident(item.item_crc16, "label", index)
		for index in range(len(item.choices_list))
	]
	# Map each correct answer text to its choice label ident.
	correct_idents = [
		label_idents[item.choices_list.index(answer_text)]
		for answer_text in item.answers_list
	]

	item_el = _new_item_element()
	item_el.append(build_itemmetadata("Multiple Answer", 1))

	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(item.question_text))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")
	# Multiple cardinality lets the student select more than one choice.
	response_lid = _build_choice_response_lid(
		response_ident, "Multiple", label_idents, item.choices_list
	)
	response_block.append(response_lid)

	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(1.0))
	# Correct branch tests every correct label ident together.
	resprocessing.append(_build_choice_correct_respcondition(correct_idents))
	resprocessing.append(build_incorrect_respcondition())
	for label_ident in label_idents:
		resprocessing.append(_build_per_choice_feedback(label_ident))

	for feedback in build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

#============================================
def _build_choice_response_lid(
	response_ident: str,
	cardinality: str,
	label_idents: list[str],
	choices_list: list[str],
) -> lxml.etree.Element:
	"""
	Build a `<response_lid>` with a `<render_choice>` of `<response_label>` choices.

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
		render_choice.append(build_response_label(label_ident, choice_html))
	return response_lid

#============================================
def _build_choice_correct_respcondition(correct_idents: list[str]) -> lxml.etree.Element:
	"""
	Build the `<respcondition title="correct">` branch for MC/MA.

	Args:
		correct_idents: The label idents that score as correct.

	Returns:
		The `<respcondition title="correct">` element.
	"""
	respcondition = lxml.etree.Element("respcondition", title="correct")
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	# One varequal per correct choice; multiple idents means additive MA scoring.
	for correct_ident in correct_idents:
		conditionvar.append(_varequal("response", correct_ident))
	setvar = lxml.etree.SubElement(respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "SCORE.max"
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "correct")
	displayfeedback.set("feedbacktype", "Response")
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
	conditionvar.append(_varequal(label_ident, None))
	setvar = lxml.etree.SubElement(respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "0"
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", label_ident)
	displayfeedback.set("feedbacktype", "Response")
	return respcondition

#============================================
def build_FIB(item: item_types.FIB) -> lxml.etree.Element:
	"""
	Build the `<item>` subtree for a Fill in the Blank question.

	Structure: one `response_str ident="response"` + `render_fib fibtype="String"`;
	one `<respcondition>` per accepted answer, each with a unique hex title and a
	`<varequal respident="response" case="No">` carrying the accepted answer text.

	Args:
		item: An `item_types.FIB` instance.

	Returns:
		The `<item>` element.
	"""
	item_el = _new_item_element()
	item_el.append(build_itemmetadata("Fill in the Blank", 1))

	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(item.question_text))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")
	# Single text-entry field keyed "response".
	response_str = lxml.etree.SubElement(response_block, "response_str", ident="response")
	response_str.set("rcardinality", "Single")
	response_str.set("rtiming", "No")
	response_str.append(build_render_fib("String"))

	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(1.0))
	# One scoring branch per accepted answer.
	for index, accepted_answer in enumerate(item.answers_list):
		title = make_ident(item.item_crc16, "fib_answer", index)
		respcondition = lxml.etree.SubElement(resprocessing, "respcondition", title=title)
		conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
		conditionvar.append(_varequal("response", accepted_answer))
		setvar = lxml.etree.SubElement(respcondition, "setvar")
		setvar.set("variablename", "SCORE")
		setvar.set("action", "Set")
		setvar.text = "SCORE.max"
		displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
		displayfeedback.set("linkrefid", "correct")
		displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(build_incorrect_respcondition())

	for feedback in build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

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

	item_el = _new_item_element()
	item_el.append(build_itemmetadata("Numeric", 1))

	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(item.question_text))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")
	# Numeric entry field keyed "response".
	response_num = lxml.etree.SubElement(response_block, "response_num", ident="response")
	response_num.set("rcardinality", "Single")
	response_num.set("rtiming", "No")
	response_num.append(build_render_fib("Decimal"))

	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(1.0))
	# Correct branch: lower <= response <= upper, plus the exact value.
	correct_title = make_ident(item.item_crc16, "num_correct", 0)
	respcondition = lxml.etree.SubElement(resprocessing, "respcondition", title=correct_title)
	conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
	vargte = lxml.etree.SubElement(conditionvar, "vargte", respident="response")
	vargte.text = _format_number(lower_bound)
	varlte = lxml.etree.SubElement(conditionvar, "varlte", respident="response")
	varlte.text = _format_number(upper_bound)
	conditionvar.append(_varequal("response", _format_number(item.answer_float)))
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "correct")
	displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(build_incorrect_respcondition())

	for feedback in build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

#============================================
def _format_number(value: float) -> str:
	"""
	Format a numeric bound for XML text, trimming trailing zeros.

	Integers render without a decimal point; non-integers keep up to six
	significant decimal places with trailing zeros removed (e.g. 38.725).

	Args:
		value: The numeric value to format.

	Returns:
		A clean numeric string.
	"""
	# Render with fixed precision, then trim trailing zeros and any bare point.
	text = f"{value:.6f}"
	text = text.rstrip("0").rstrip(".")
	# A value that trimmed to empty (e.g. 0.000000) becomes "0".
	if text == "" or text == "-":
		text = "0"
	return text

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

	item_el = _new_item_element()
	item_el.append(build_itemmetadata("Fill in the Blank Plus", blank_count))

	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(item.question_text))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")
	# One text-entry field per blank, keyed by the blank label.
	for blank_key in blank_keys:
		response_str = lxml.etree.SubElement(response_block, "response_str", ident=blank_key)
		response_str.set("rcardinality", "Single")
		response_str.set("rtiming", "No")
		response_str.append(build_render_fib("String"))

	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(float(blank_count)))
	# Correct branch: an <and> of one <or> per blank.
	correct_respcondition = lxml.etree.SubElement(resprocessing, "respcondition", title="correct")
	conditionvar = lxml.etree.SubElement(correct_respcondition, "conditionvar")
	and_el = lxml.etree.SubElement(conditionvar, "and")
	for blank_key in blank_keys:
		or_el = lxml.etree.SubElement(and_el, "or")
		# Each accepted answer for this blank is one varequal inside the <or>.
		for accepted_answer in item.answer_map[blank_key]:
			or_el.append(_varequal(blank_key, accepted_answer))
	setvar = lxml.etree.SubElement(correct_respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "SCORE.max"
	displayfeedback = lxml.etree.SubElement(correct_respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "correct")
	displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(build_incorrect_respcondition())

	for feedback in build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el

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

	item_el = _new_item_element()
	item_el.append(build_itemmetadata("Matching", 1))

	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(item.question_text))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")

	# Track each prompt's correct-label ident for the resprocessing branches.
	prompt_response_idents = []
	correct_label_idents = []
	for prompt_index, prompt_html in enumerate(prompts):
		prompt_response_ident = make_ident(item.item_crc16, "match_prompt", prompt_index)
		prompt_response_idents.append(prompt_response_ident)
		# One label ident per choice, unique to this prompt and positional.
		prompt_label_idents = [
			make_ident(item.item_crc16, f"match_label_{prompt_index}", choice_index)
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
		prompt_flow.append(build_formatted_text_flow(prompt_html))

	# Right-side choice texts, in choices_list order, indexed positionally.
	right_match_block = lxml.etree.SubElement(response_block, "flow")
	right_match_block.set("class", "RIGHT_MATCH_BLOCK")
	for choice_html in choices:
		choice_flow = lxml.etree.SubElement(right_match_block, "flow")
		choice_flow.set("class", "Block")
		choice_flow.append(build_formatted_text_flow(choice_html))

	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(1.0))
	# One scoring branch per prompt: prompt ident -> its correct label ident.
	for prompt_response_ident, correct_label_ident in zip(prompt_response_idents, correct_label_idents):
		respcondition = lxml.etree.SubElement(resprocessing, "respcondition")
		conditionvar = lxml.etree.SubElement(respcondition, "conditionvar")
		conditionvar.append(_varequal(prompt_response_ident, correct_label_ident))
		displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
		displayfeedback.set("linkrefid", "correct")
		displayfeedback.set("feedbacktype", "Response")
	resprocessing.append(build_incorrect_respcondition())

	for feedback in build_simple_itemfeedback():
		item_el.append(feedback)
	return item_el
