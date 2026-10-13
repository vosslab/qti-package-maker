"""Parse Blackboard pool item XML into internal ItemBank item types."""

# Standard Library
import collections.abc
import os

# PIP3 modules
import lxml.html
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import inline_css
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types
from qti_package_maker.common import media_assets

#============================================
def _parse_pool_into_bank(
	pool_dat_path: str,
	new_item_bank: item_bank.ItemBank,
	src_map_fn: collections.abc.Callable[[str], str],
) -> None:
	"""
	Parse every `<item>` in one pool `.dat` and add the items to the bank.

	Args:
		pool_dat_path: Path to a pool `.dat` (the `assessment/x-bb-qti-pool` XML).
		new_item_bank: The ItemBank to add parsed items to.
		src_map_fn: Rewrites `<img src>` values while extracting item HTML (the
			identity function when the pool carries no images).
	"""
	tree = lxml.etree.parse(pool_dat_path)
	root = tree.getroot()
	dat_filename = os.path.basename(pool_dat_path)
	# Each question is one <item>; iterate them in document order.
	for item_index, item_el in enumerate(root.iter("item")):
		item_cls = _parse_one_item(item_el, dat_filename, item_index, src_map_fn)
		# A None result means the item was skipped (unknown type or malformed);
		# the per-item helper already warned with the source name.
		if item_cls is not None:
			new_item_bank.add_item_cls(item_cls)

#============================================
def _parse_one_item(
	item_el: lxml.etree.Element,
	dat_filename: str,
	item_index: int,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.BaseItem | None:
	"""
	Parse a single `<item>` element into an internal item, or skip it.

	Args:
		item_el: The `<item>` lxml element.
		dat_filename: The pool `.dat` filename, used in warning messages.
		item_index: The item's positional index, used in warning messages.
		src_map_fn: Rewrites `<img src>` values while extracting item HTML.

	Returns:
		The parsed item instance, or None when the item is skipped (unknown
		question type or malformed content).
	"""
	source = f"{dat_filename} item #{item_index + 1}"
	question_type = item_el.findtext("itemmetadata/bbmd_questiontype")
	# A missing type marker means we cannot dispatch; skip with a clear warning.
	if question_type is None:
		print(f"Warning: skipping {source}: no bbmd_questiontype element")
		return None
	question_type = question_type.strip()
	read_function = _QUESTION_TYPE_DISPATCH.get(question_type)
	if read_function is None:
		print(
			f"Warning: skipping {source}: unknown bbmd_questiontype "
			f"'{question_type}'"
		)
		return None
	# A malformed item body raises during parsing; catch it narrowly so one bad
	# item does not abort the whole pool, and name the source in the warning.
	try:
		item_cls = read_function(item_el, src_map_fn)
	except inline_css.InlineCssError:
		raise
	except (ValueError, IndexError, KeyError, AttributeError) as exc:
		print(f"Warning: skipping malformed {source}: {exc}")
		return None
	return item_cls

#============================================
# Shared element-text extraction helpers
#============================================
#============================================
def _smart_text(
	material_owner: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> str:
	"""
	Read the HTML payload from the first SMART_TEXT material under an element.

	The write path stores HTML as the `.text` of a
	`mat_formattedtext type="SMART_TEXT"`; lxml escaped it once on write and
	un-escapes it once here, recovering the original HTML verbatim.

	Args:
		material_owner: An element whose subtree contains a
			`mat_formattedtext` element (a flow, response_label, etc.).
		src_map_fn: Rewrites any `<img src>` found in the recovered HTML (the
			identity function when the pool carries no images).

	Returns:
		The un-escaped HTML string (empty string when the carrier is empty),
		with `<img src>` values rewritten by src_map_fn.
	"""
	# The first SMART_TEXT carrier anywhere beneath this element holds the HTML.
	mat = material_owner.find(".//mat_formattedtext")
	if mat is None:
		raise ValueError("no mat_formattedtext element found")
	# lxml returns the un-escaped text; None text (empty element) reads as "".
	html_text = mat.text if mat.text is not None else ""
	# Real Blackboard exports carry unclosed void elements (<br>, <img ...>),
	# which item construction rejects (every HTML field is validated as XML);
	# self-close them before any src rewriting.
	html_text = _repair_html_void_elements(html_text)
	# Cheap no-op when html_text carries no <img> tag; rewrites csfiles tokens
	# to their recovered plain filenames otherwise.
	return media_assets.rewrite_html_srcs(html_text, src_map_fn)

#============================================
def _repair_html_void_elements(html_str: str) -> str:
	"""
	Self-close unclosed void HTML elements so html_str parses as valid XML.

	Real Blackboard-exported HTML writes void elements like `<br>` and
	`<img src="...">` without a self-closing slash; `item_types` construction
	validates every HTML field as XML (`validator.validate_html`), which
	rejects them. Re-serializing through lxml.html repairs this, but the
	lxml.html/libxml2 parser also normalizes markup while it does so: every
	element and attribute name is lowercased (`<STRONG>` becomes `<strong>`,
	`SRC=` becomes `src=`), and any decoded entity is re-escaped as an ASCII
	numeric character reference (see the `&nbsp;` handling below). Attribute
	VALUES, attribute order, and visible text content are preserved.

	Args:
		html_str: an HTML-bearing field (already src-rewritten).

	Returns:
		The same content with every void element self-closed and element/
		attribute names lowercased; a payload with no `<` is returned
		unchanged.
	"""
	# fast exit: plain text carries nothing to repair
	if "<" not in html_str:
		return html_str
	# wrap so lxml.html parses a fragment, not a full document
	wrapped = f"<div>{html_str}</div>"
	root = lxml.html.fromstring(wrapped)
	parts = []
	# text before the first child sits on the wrapper's own .text; a named
	# entity like &nbsp; decodes to a literal non-ASCII char during parsing
	# (item construction requires ASCII), so re-escape it as a numeric ref.
	if root.text:
		parts.append(root.text.encode("ascii", "xmlcharrefreplace").decode("ascii"))
	for child in root:
		# encoding="ascii" both self-closes void elements (method="xml") and
		# re-escapes any decoded entity (e.g. &nbsp;) as an ASCII-safe numeric
		# character reference instead of a literal non-ASCII byte.
		child_bytes = lxml.html.tostring(child, encoding="ascii", method="xml")
		parts.append(child_bytes.decode("ascii"))
	return "".join(parts)

#============================================
def _question_html(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> str:
	"""
	Read the question HTML from an item's `QUESTION_BLOCK`.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the recovered HTML.

	Returns:
		The un-escaped question HTML.
	"""
	# The question text lives in the single flow class="QUESTION_BLOCK".
	question_block = _find_flow_by_class(item_el, "QUESTION_BLOCK")
	if question_block is None:
		raise ValueError("no QUESTION_BLOCK flow found")
	return _smart_text(question_block, src_map_fn)

#============================================
def _find_flow_by_class(parent: lxml.etree.Element, class_value: str) -> lxml.etree.Element | None:
	"""
	Find the first descendant `<flow>` with the given `class` attribute.

	Args:
		parent: The element to search beneath.
		class_value: The `class` attribute value to match.

	Returns:
		The matching `<flow>` element, or None when none is found.
	"""
	for flow in parent.iter("flow"):
		if flow.get("class") == class_value:
			return flow
	return None

#============================================
def _resprocessing(item_el: lxml.etree.Element) -> lxml.etree.Element:
	"""
	Return the item's `<resprocessing>` element.

	Args:
		item_el: The `<item>` element.

	Returns:
		The `<resprocessing>` element.
	"""
	resprocessing = item_el.find("resprocessing")
	if resprocessing is None:
		raise ValueError("no resprocessing element found")
	return resprocessing

#============================================
# Choice-based readers (MC / MA)
#============================================
#============================================
def _choice_response_lid(item_el: lxml.etree.Element) -> lxml.etree.Element:
	"""
	Return the single choice `<response_lid>` for an MC/MA item.

	The choice response_lid is the one whose `render_choice` holds
	`response_label` choices directly (MATCH uses one response_lid per prompt and
	is handled separately).

	Args:
		item_el: The `<item>` element.

	Returns:
		The choice `<response_lid>` element.
	"""
	presentation = item_el.find("presentation")
	if presentation is None:
		raise ValueError("no presentation element found")
	# An MC/MA item has exactly one response_lid; take the first.
	response_lid = presentation.find(".//response_lid")
	if response_lid is None:
		raise ValueError("no response_lid element found for choice question")
	return response_lid

#============================================
def _read_choice_labels(
	response_lid: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> tuple[list[str], list[str]]:
	"""
	Read the choice idents and choice HTML texts from a choice `response_lid`.

	Args:
		response_lid: The choice `<response_lid>` element.
		src_map_fn: Rewrites any `<img src>` found in each choice's HTML.

	Returns:
		A tuple of (label idents, choice HTML strings), index-aligned.
	"""
	label_idents = []
	choice_texts = []
	# Each response_label is one choice; its ident keys scoring, its text is shown.
	for response_label in response_lid.iter("response_label"):
		label_idents.append(response_label.get("ident"))
		choice_texts.append(_smart_text(response_label, src_map_fn))
	if not choice_texts:
		raise ValueError("choice question has no response_label choices")
	return label_idents, choice_texts

#============================================
def _is_descendant_of_not(
	varequal_el: lxml.etree.Element,
	stop_el: lxml.etree.Element,
) -> bool:
	"""
	Return True if varequal_el has a `<not>` ancestor between itself and stop_el.

	Real Blackboard MA wraps incorrect choices in `<not><varequal .../></not>`
	inside the `<and>` of the `title="correct"` branch. Walking the parent chain
	from the varequal up to (but not including) the respcondition detects these
	negated choices so the reader can skip them.

	Args:
		varequal_el: The varequal element to test.
		stop_el: The respcondition element that is the boundary; the walk stops
			before reaching it.

	Returns:
		True when varequal_el is nested inside a `<not>` on the path to stop_el.
	"""
	parent = varequal_el.getparent()
	while parent is not None and parent is not stop_el:
		if parent.tag == "not":
			return True
		parent = parent.getparent()
	return False

#============================================
def _correct_choice_idents(item_el: lxml.etree.Element) -> list[str]:
	"""
	Read the correct label idents from the `title="correct"` resprocessing branch.

	For real Blackboard MA the `title="correct"` branch holds an `<and>` whose
	children list every choice: correct choices as bare `<varequal
	respident="response" case="No">IDENT</varequal>`, incorrect choices wrapped in
	`<not><varequal .../></not>`. Only the non-negated varequals name correct
	answers. For legacy engine-emitted MA (bare varequals in `<conditionvar>`
	without any `<and>` or `<not>`) the same predicate keeps all varequals because
	none has a `<not>` ancestor.

	Args:
		item_el: The `<item>` element.

	Returns:
		The correct label idents, in branch order.
	"""
	resprocessing = _resprocessing(item_el)
	correct_idents = []
	# The correct branch is titled "correct"; only non-negated varequal texts name answers.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") != "correct":
			continue
		for varequal in respcondition.iter("varequal"):
			# Skip varequals nested inside a <not>: those are incorrect choices in real BB MA.
			if _is_descendant_of_not(varequal, respcondition):
				continue
			if varequal.text:
				correct_idents.append(varequal.text.strip())
	if not correct_idents:
		raise ValueError("no correct varequal idents found in resprocessing")
	return correct_idents

#============================================
def _is_multiple_cardinality(response_lid: lxml.etree.Element) -> bool:
	"""
	Report whether a choice `response_lid` allows multiple selections (MA).

	Args:
		response_lid: The choice `<response_lid>` element.

	Returns:
		True when `rcardinality="Multiple"` (Multiple Answer), else False.
	"""
	return response_lid.get("rcardinality") == "Multiple"

#============================================
def _read_choice_item(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.BaseItem:
	"""
	Read an MC or MA item, choosing the type from the response cardinality.

	`rcardinality="Multiple"` is MA; otherwise MC. This refines the
	`bbmd_questiontype` marker, which Blackboard sometimes labels "Multiple
	Choice" even for multi-select questions.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the item's HTML.

	Returns:
		An MC or MA item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	response_lid = _choice_response_lid(item_el)
	label_idents, choice_texts = _read_choice_labels(response_lid, src_map_fn)
	correct_idents = _correct_choice_idents(item_el)
	# Map correct idents back to their choice texts via positional alignment.
	ident_to_text = dict(zip(label_idents, choice_texts))
	correct_texts = [
		ident_to_text[correct_ident]
		for correct_ident in correct_idents
		if correct_ident in ident_to_text
	]
	if not correct_texts:
		raise ValueError("correct idents did not match any choice label")
	# Multiple-cardinality or more than one correct answer means MA.
	if _is_multiple_cardinality(response_lid) or len(correct_texts) > 1:
		return item_types.MA(question_html, choice_texts, correct_texts)
	return item_types.MC(question_html, choice_texts, correct_texts[0])

#============================================
# Fill-in-the-blank readers (FIB / MULTI_FIB)
#============================================
#============================================
def _read_FIB(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.FIB:
	"""
	Read a Fill in the Blank item.

	Each accepted answer is the text of a `<varequal respident="response">` in
	its own (UUID-titled) respcondition; the `incorrect` branch is excluded.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the question HTML.

	Returns:
		A FIB item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	resprocessing = _resprocessing(item_el)
	answers_list = []
	# Every non-incorrect branch carries one accepted answer for the response field.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "incorrect":
			continue
		for varequal in respcondition.iter("varequal"):
			if varequal.get("respident") == "response" and varequal.text:
				answers_list.append(varequal.text)
	if not answers_list:
		raise ValueError("FIB item has no accepted answers")
	return item_types.FIB(question_html, answers_list)

#============================================
def _read_MULTI_FIB(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.MULTI_FIB:
	"""
	Read a Fill in the Blank Plus item.

	The `title="correct"` branch holds an `<and>` of one `<or>` per blank; each
	`<or>` carries one `<varequal respident="KEY">` per accepted answer for that
	blank. The answer_map keys are the per-blank `respident` values.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the question HTML.

	Returns:
		A MULTI_FIB item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	resprocessing = _resprocessing(item_el)
	# Find the correct branch holding the <and> of <or> blank groups.
	correct_branch = None
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "correct":
			correct_branch = respcondition
			break
	if correct_branch is None:
		raise ValueError("MULTI_FIB item has no title='correct' branch")
	answer_map: dict[str, list[str]] = {}
	# Each <or> group is one blank; its varequal respident is the blank key.
	for or_group in correct_branch.iter("or"):
		for varequal in or_group.iter("varequal"):
			blank_key = varequal.get("respident")
			if blank_key is None or varequal.text is None:
				continue
			# Preserve insertion order; collect every accepted spelling per blank.
			answer_map.setdefault(blank_key, []).append(varequal.text)
	if not answer_map:
		raise ValueError("MULTI_FIB item recovered no blank answer groups")
	return item_types.MULTI_FIB(question_html, answer_map)

#============================================
# Numeric reader (NUM)
#============================================
#============================================
def _read_NUM(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.NUM:
	"""
	Read a Numeric item.

	The correct branch is any `<respcondition>` that is NOT titled "incorrect"
	and carries `<vargte>` or `<varequal>`. Real samples use a UUID title on the
	correct branch, not `title="correct"`. Once found, the branch carries
	`<vargte>` (answer - tolerance), `<varlte>` (answer + tolerance), and
	`<varequal>` (the exact answer). The answer is the varequal value; the
	tolerance is half the (varlte - vargte) window.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the question HTML.

	Returns:
		A NUM item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	resprocessing = _resprocessing(item_el)
	# The numeric correct branch is the one that is not titled "incorrect".
	correct_branch = None
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "incorrect":
			continue
		# The numeric branch is identified by carrying the bound conditions.
		if respcondition.find(".//vargte") is not None or respcondition.find(".//varequal") is not None:
			correct_branch = respcondition
			break
	if correct_branch is None:
		raise ValueError("NUM item has no correct respcondition")
	varequal = correct_branch.find(".//varequal")
	if varequal is None or varequal.text is None:
		raise ValueError("NUM item correct branch has no varequal answer")
	answer_float = float(varequal.text)
	# Recover the tolerance from the bound window when both bounds are present.
	vargte = correct_branch.find(".//vargte")
	varlte = correct_branch.find(".//varlte")
	if vargte is not None and vargte.text and varlte is not None and varlte.text:
		lower_bound = float(vargte.text)
		upper_bound = float(varlte.text)
		tolerance_float = (upper_bound - lower_bound) / 2.0
	else:
		# No bound window means an exact-match numeric; zero tolerance.
		tolerance_float = 0.0
	return item_types.NUM(question_html, answer_float, tolerance_float)

#============================================
# Matching reader (MATCH)
#============================================
#============================================
def _read_MATCH(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.MATCH:
	"""
	Read a Matching item, recovering the prompt->choice pairing.

	Each prompt is a `<flow class="Block">` holding a `response_lid` (whose
	`render_choice` lists one `response_label` per right-side choice) followed by
	the prompt's own FORMATTED_TEXT_BLOCK. A sibling
	`<flow class="RIGHT_MATCH_BLOCK">` lists the choice texts in order.

	Pairing recovery: each prompt's `response_lid` ident appears as the
	`respident` of a `<varequal>` in `resprocessing`; that varequal's TEXT is the
	correct label ident. The label ident's position within the prompt's
	`response_label` list indexes the `RIGHT_MATCH_BLOCK` choice texts, recovering
	the prompt's matching choice. The returned MATCH stores prompts and choices in
	prompt order, so prompts_list[i] pairs with choices_list[i].

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the item's HTML.

	Returns:
		A MATCH item instance with prompts and choices in paired order.
	"""
	question_html = _question_html(item_el, src_map_fn)
	# RIGHT_MATCH_BLOCK is a sibling of RESPONSE_BLOCK in the real samples but a
	# child of it in the engine's own output; search the whole item so both
	# placements resolve. There is exactly one RIGHT_MATCH_BLOCK per item.
	presentation = item_el.find("presentation")
	if presentation is None:
		raise ValueError("MATCH item has no presentation")
	right_match_block = _find_flow_by_class(presentation, "RIGHT_MATCH_BLOCK")
	if right_match_block is None:
		raise ValueError("MATCH item has no RIGHT_MATCH_BLOCK")
	# The right-side choice texts, indexed positionally as written.
	choice_texts = _read_right_match_texts(right_match_block, src_map_fn)

	# Map each prompt's response_lid ident -> its correct label ident.
	correct_ident_by_prompt = _match_correct_idents(item_el)

	prompts_list = []
	choices_list = []
	# Each prompt block holds one response_lid and the prompt's display text.
	for prompt_block in _match_prompt_blocks(presentation):
		prompt_response_lid = prompt_block.find(".//response_lid")
		if prompt_response_lid is None:
			raise ValueError("MATCH prompt block has no response_lid")
		prompt_lid_ident = prompt_response_lid.get("ident")
		# The prompt's display text is its FORMATTED_TEXT_BLOCK (after the lid).
		prompt_text = _match_prompt_text(prompt_block, src_map_fn)
		# The label idents in this prompt, positionally aligned to the choices.
		label_idents = [
			label.get("ident")
			for label in prompt_response_lid.iter("response_label")
		]
		correct_label_ident = correct_ident_by_prompt.get(prompt_lid_ident)
		if correct_label_ident is None:
			raise ValueError(
				f"MATCH prompt '{prompt_lid_ident}' has no scoring varequal"
			)
		if correct_label_ident not in label_idents:
			raise ValueError(
				f"MATCH prompt '{prompt_lid_ident}' correct ident not in its labels"
			)
		# The label's position indexes the RIGHT_MATCH_BLOCK choice list.
		choice_index = label_idents.index(correct_label_ident)
		if choice_index >= len(choice_texts):
			raise ValueError("MATCH correct choice index out of range")
		prompts_list.append(prompt_text)
		choices_list.append(choice_texts[choice_index])
	if not prompts_list:
		raise ValueError("MATCH item recovered no prompts")
	return item_types.MATCH(question_html, prompts_list, choices_list)

#============================================
def _read_right_match_texts(
	right_match_block: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> list[str]:
	"""
	Read the right-side choice texts from a `RIGHT_MATCH_BLOCK`, in order.

	Args:
		right_match_block: The `<flow class="RIGHT_MATCH_BLOCK">` element.
		src_map_fn: Rewrites any `<img src>` found in each choice's HTML.

	Returns:
		The choice HTML strings, in document order.
	"""
	choice_texts = []
	# Each direct child flow class="Block" is one choice's formatted text.
	for choice_flow in right_match_block.findall("flow"):
		choice_texts.append(_smart_text(choice_flow, src_map_fn))
	if not choice_texts:
		raise ValueError("RIGHT_MATCH_BLOCK has no choice texts")
	return choice_texts

#============================================
def _match_prompt_blocks(presentation: lxml.etree.Element) -> list[lxml.etree.Element]:
	"""
	Return the per-prompt `<flow class="Block">` blocks of a MATCH item.

	A MATCH item has one `flow class="Block"` per prompt, each holding a direct
	`response_lid` child, alongside a `RIGHT_MATCH_BLOCK` whose own inner Block
	flows carry no response_lid. A prompt block is a Block flow with a
	response_lid as a direct child; this selects the prompt blocks regardless of
	whether RIGHT_MATCH_BLOCK is a sibling (real samples) or a child (engine
	output) of RESPONSE_BLOCK.

	Args:
		presentation: The `<presentation>` element.

	Returns:
		The per-prompt block elements, in document order.
	"""
	prompt_blocks = []
	# A prompt block is a Block flow whose direct child is a response_lid.
	for block in presentation.iter("flow"):
		if block.get("class") != "Block":
			continue
		if block.find("response_lid") is not None:
			prompt_blocks.append(block)
	return prompt_blocks

#============================================
def _match_prompt_text(
	prompt_block: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> str:
	"""
	Read a MATCH prompt's display text from its FORMATTED_TEXT_BLOCK.

	The prompt block holds the response_lid first, then a sibling
	`flow class="FORMATTED_TEXT_BLOCK"` carrying the prompt's own SMART_TEXT.

	Args:
		prompt_block: The per-prompt `<flow class="Block">` element.
		src_map_fn: Rewrites any `<img src>` found in the prompt's HTML.

	Returns:
		The un-escaped prompt HTML.
	"""
	# The prompt's display text is the FORMATTED_TEXT_BLOCK that is a direct
	# child of the prompt block (not the one nested inside the response_lid).
	for flow in prompt_block.findall("flow"):
		if flow.get("class") == "FORMATTED_TEXT_BLOCK":
			return _smart_text(flow, src_map_fn)
	raise ValueError("MATCH prompt block has no FORMATTED_TEXT_BLOCK display text")

#============================================
def _match_correct_idents(item_el: lxml.etree.Element) -> dict[str, str]:
	"""
	Map each MATCH prompt's response_lid ident to its correct label ident.

	The samples score MATCH via one untitled `respcondition` per prompt, each
	holding a `<varequal respident="PROMPT_LID">CORRECT_LABEL_IDENT</varequal>`.
	The `incorrect` branch is skipped.

	Args:
		item_el: The `<item>` element.

	Returns:
		A dict of {prompt response_lid ident: correct label ident}.
	"""
	resprocessing = _resprocessing(item_el)
	correct_by_prompt = {}
	# Each prompt scoring branch keys prompt-lid ident -> correct label ident.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "incorrect":
			continue
		for varequal in respcondition.iter("varequal"):
			prompt_ident = varequal.get("respident")
			if prompt_ident is not None and varequal.text:
				correct_by_prompt[prompt_ident] = varequal.text.strip()
	return correct_by_prompt

#============================================
# Question-type dispatch table
#============================================
# Maps the `<bbmd_questiontype>` element value to its reader. MC/MA share one
# reader that refines the type by response cardinality; True/False maps to MC.
_QUESTION_TYPE_DISPATCH = {
	"Multiple Choice": _read_choice_item,
	"Multiple Answer": _read_choice_item,
	"Fill in the Blank": _read_FIB,
	"Fill in the Blank Plus": _read_MULTI_FIB,
	"Numeric": _read_NUM,
	"Matching": _read_MATCH,
	"True/False": _read_choice_item,
}
