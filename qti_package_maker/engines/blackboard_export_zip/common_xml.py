"""
Shared Blackboard pool XML primitives used by the per-type builders.

This module holds the low-level element builders and the per-item skeleton that
every `build_<type>` function in the sibling per-type modules (`MC.py`, `MA.py`,
`MATCH.py`, `FIB.py`, `NUM.py`, `MULTI_FIB.py`) reuses. It carries no per-type
logic of its own; each per-type module imports this module and assembles its
own resprocessing branches on top of the shared scaffolding.

The dialect reuses the QTI-1.2 ASI envelope (`questestinterop`, `response_lid`,
`render_choice`, `resprocessing`, `varequal`) but the payload is
Blackboard-specific: `bbmd_*` itemmetadata, `mat_formattedtext type="SMART_TEXT"`
HTML carriers, `flow class` block nesting, and `RIGHT_MATCH_BLOCK` for matching.
The schema is shaped from byte-level study of real sample pools under
`BB_Export_ZIP/`; it is NOT QTI 2.1 and shares no builder with the QTI 2.1
engines. See `docs/active_plans/audits/blackboard_export_zip_forgeability.md`.
"""

# PIP3 modules
import lxml.html
import lxml.etree

# QTI Package Maker
from qti_package_maker.common import string_functions

#============================================
# Table whitespace sanitation for Blackboard Ultra
#============================================
# Blackboard Ultra's question-expand HTML renderer crashes ("Oops! Something
# broke.") on a specific malformed-table pattern. The crash requires all three:
#   1. the <table> carries a text-align style (any value),
#   2. a whitespace-only text node sits directly inside a <tr> (for example a
#      space between the <tr> and its first <td>, or between two cells),
#   3. the <tr> does NOT end with whitespace before </tr> (a "tight close").
# Such text directly inside a <tr> is invalid HTML (the parser foster-parents it),
# and the combination above wedges Ultra's table layout. The list view survives
# because it strips HTML; only expanding the question parses the full markup and
# dies. The crash hits MC, MA, and NUM items (FIB renders the question
# differently and is unaffected). Proven by single-character minimal cases:
# `<table style="text-align:center"><tr> <td>x</td></tr>` crashes, and removing
# the leading space, removing the text-align, or adding a trailing space before
# </tr> each makes it render. The fix is deliberately broader than the exact
# trigger: rather than detect the precise text-align-plus-tight-close combination,
# it removes EVERY whitespace-only text node that sits directly inside a
# table-structure element (such text is invalid HTML regardless). That deletes the
# trigger outright while preserving all cell content, inline styles, and markup.

# Table-structure elements that must not carry whitespace-only text nodes as
# direct children (whitespace between cells/rows is invalid and triggers the crash).
_TABLE_STRUCTURE_TAGS = ("table", "thead", "tbody", "tfoot", "tr")

#============================================
def sanitize_question_html(html_payload: str) -> str:
	"""
	Remove whitespace-only text nodes that sit directly inside table structure.

	Only table-containing payloads are processed: such a payload is re-serialized
	through lxml.html with whitespace-only text nodes that are direct children of
	<table>/<thead>/<tbody>/<tfoot>/<tr> dropped. Such text is invalid HTML and
	crashes the Blackboard Ultra expand renderer for MC/MA/NUM items when the table
	also carries a text-align style. Whitespace inside cells (<td>/<th> content) is
	preserved, as are all styles and markup. Any payload without a <table> (plain
	text, or inline markup like <sup>/<b>/RDKit spans) is returned verbatim so the
	lxml round-trip never alters non-table content.

	Args:
		html_payload: The question/choice HTML string.

	Returns:
		The HTML with invalid table-structure whitespace removed, or the payload
		unchanged when it contains no <table>.
	"""
	# Only a <table> can carry the crash trigger. Return everything else verbatim
	# so non-table markup never passes through the lxml parse/re-serialize round-trip.
	if "<table" not in html_payload.lower():
		return html_payload
	# Wrap in a container so lxml parses a fragment, not a full document.
	wrapped = f"<div>{html_payload}</div>"
	root = lxml.html.fromstring(wrapped)
	# Null out whitespace-only text directly inside table-structure elements:
	# the element's own leading text (before its first child) and each child's
	# tail (the text that follows it, before the next sibling or the close tag).
	for element in root.iter(*_TABLE_STRUCTURE_TAGS):
		if element.text is not None and element.text.strip() == "":
			element.text = None
		for child in element:
			if child.tail is not None and child.tail.strip() == "":
				child.tail = None
	# Rebuild the inner HTML of the wrapper, dropping the wrapper element itself.
	parts = []
	# Text before the first child is stored on the wrapper's own .text.
	if root.text:
		parts.append(root.text)
	for child in root:
		child_html = lxml.html.tostring(child, encoding="unicode", method="html")
		parts.append(child_html)
	sanitized = "".join(parts)
	return sanitized

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
	# Strip whitespace-only text nodes inside table structure (e.g. a space
	# between a <tr> and its first cell) so the Blackboard Ultra renderer does not
	# crash when the question is expanded.
	safe_payload = sanitize_question_html(html_payload)
	# Assigning to .text makes lxml escape the HTML once on serialization.
	mat_formattedtext.text = safe_payload
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
def _not(child: lxml.etree.Element) -> lxml.etree.Element:
	"""
	Wrap a condition element in a `<not>` negation.

	Real Blackboard MA negates each incorrect choice inside the `<and>` of the
	`title="correct"` branch as `<not><varequal .../></not>`.

	Args:
		child: The condition element to negate (a `<varequal>`).

	Returns:
		The `<not>` element wrapping the child.
	"""
	not_el = lxml.etree.Element("not")
	not_el.append(child)
	return not_el

#============================================
def build_correct_setvar_and_feedback(respcondition: lxml.etree.Element) -> None:
	"""
	Append the shared `setvar SCORE.max` + `displayfeedback linkrefid="correct"`.

	This is the trailing pair every `title="correct"` choice branch carries
	(MC and MA both end this way); factoring it keeps the MC and MA helpers DRY
	without sharing their differing conditionvar bodies.

	Args:
		respcondition: The `<respcondition title="correct">` element to extend.
	"""
	setvar = lxml.etree.SubElement(respcondition, "setvar")
	setvar.set("variablename", "SCORE")
	setvar.set("action", "Set")
	setvar.text = "SCORE.max"
	displayfeedback = lxml.etree.SubElement(respcondition, "displayfeedback")
	displayfeedback.set("linkrefid", "correct")
	displayfeedback.set("feedbacktype", "Response")

#============================================
def format_number(value: float) -> str:
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
# Shared per-item skeleton
#============================================
#============================================
def build_item_skeleton(
	question_type: str,
	absolutescore_max: int,
	question_html: str,
) -> tuple[lxml.etree.Element, lxml.etree.Element, lxml.etree.Element]:
	"""
	Build the shared per-item skeleton every Blackboard pool builder starts with.

	Every `build_<type>` repeats the same opening scaffolding:
	`_new_item_element` -> `build_itemmetadata` -> `presentation` with an outer
	`flow class="Block"` -> `build_question_block` -> a `flow class="RESPONSE_BLOCK"`
	child of the outer flow. This helper assembles that scaffolding once so the
	per-type modules add only their own response fields and resprocessing on top.

	Args:
		question_type: The `bbmd_questiontype` marker (e.g. "Multiple Choice").
		absolutescore_max: The `qmd_absolutescore_max` weight (1, or blank count).
		question_html: The question text HTML.

	Returns:
		A `(item_el, outer_flow, response_block)` tuple:
		- item_el: the root `<item>` element with itemmetadata + presentation.
		- outer_flow: the outer `<flow class="Block">` (parent of RESPONSE_BLOCK;
			MATCH attaches its sibling RIGHT_MATCH_BLOCK here).
		- response_block: the `<flow class="RESPONSE_BLOCK">` for response fields.
	"""
	item_el = _new_item_element()
	item_el.append(build_itemmetadata(question_type, absolutescore_max))

	# Presentation: question block + a response block, both under one outer flow.
	presentation = lxml.etree.SubElement(item_el, "presentation")
	outer_flow = lxml.etree.SubElement(presentation, "flow")
	outer_flow.set("class", "Block")
	outer_flow.append(build_question_block(question_html))
	response_block = lxml.etree.SubElement(outer_flow, "flow")
	response_block.set("class", "RESPONSE_BLOCK")
	return item_el, outer_flow, response_block

#============================================
def start_resprocessing(
	item_el: lxml.etree.Element,
	max_score: float,
) -> lxml.etree.Element:
	"""
	Append the `<resprocessing>` block (with its `<outcomes>`) to an item.

	Every builder opens resprocessing the same way: a
	`<resprocessing scoremodel="SumOfScores">` carrying one `<outcomes>` SCORE
	declaration, then per-type scoring branches. This helper creates that opening
	and returns the resprocessing element so each builder appends its own branches.

	Args:
		item_el: The root `<item>` element to extend.
		max_score: The maximum score used for the `<outcomes>` maxvalue.

	Returns:
		The `<resprocessing>` element ready for per-type branches.
	"""
	resprocessing = lxml.etree.SubElement(item_el, "resprocessing", scoremodel="SumOfScores")
	resprocessing.append(build_outcomes(max_score))
	return resprocessing
