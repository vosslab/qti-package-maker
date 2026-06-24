"""
Read a Blackboard Original pool-export package back into an ItemBank.

This module is the inverse of the write path (`item_xml_helpers.py` +
`assessment_meta.py`). It accepts either a Blackboard pool-export ZIP
(`Pool_ExportFile_*.zip`) or an already-unzipped pool directory, locates the
`assessment/x-bb-qti-pool` resource through `imsmanifest.xml`, and parses each
`<item>` in the pool `.dat` into an internal `item_types.*` instance.

The pool dialect is the QTI-1.2-derived envelope with Blackboard extensions
that `item_xml_helpers.py` writes (and that the real sample pools under
`BB_Export_ZIP/` carry). The reader keys each item on its `<bbmd_questiontype>`
ELEMENT value (not an attribute), recovers question/choice HTML by reading the
`mat_formattedtext` element text (lxml un-escapes it once, reversing the
single-escape the write path applies), and recovers correct answers from the
`resprocessing` `varequal` conditions.

Type dispatch (from the forgeability audit and the real samples):

- `Multiple Choice` -> MC when the choice `response_lid` is `rcardinality="Single"`,
  MA when it is `rcardinality="Multiple"`.
- `Multiple Answer` -> MA.
- `Fill in the Blank` -> FIB (one `response_str` + per-answer `varequal`).
- `Numeric` -> NUM (answer from `varequal`, tolerance from the vargte/varlte window).
- `Fill in the Blank Plus` -> MULTI_FIB (per-blank `respident` keys, `<and>` of `<or>`).
- `Matching` -> MATCH (prompt->choice pairing recovered via each prompt
  `response_lid` ident's `varequal` answer ident, mapped back to its position
  and the `RIGHT_MATCH_BLOCK` text).
- `True/False` -> MC (the internal model has no T/F type).

Edge cases are surfaced, never silently swallowed: a missing or empty manifest
pool entry raises; multiple pool resources are read into one combined ItemBank;
an unparseable item is skipped with a warning naming its source; an unknown
`bbmd_questiontype` is skipped with a warning naming the type and source item;
duplicate `item_crc16` collisions are handled by `ItemBank` dedup (logged there).
"""

# Standard Library
import os
import zipfile
import tempfile

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types

#============================================
# Manifest / namespace constants
#============================================
# Blackboard's content-packaging namespace; the manifest declares it as `bb:`.
BB_NAMESPACE = "http://www.blackboard.com/content-packaging/"
# The manifest resource that carries the question pool.
POOL_RESOURCE_TYPE = "assessment/x-bb-qti-pool"
# The manifest filename inside every pool package.
MANIFEST_FILENAME = "imsmanifest.xml"

#============================================
# Public entry point
#============================================
#============================================
def read_items_from_file(infile: str, allow_mixed: bool = False) -> item_bank.ItemBank:
	"""
	Read a Blackboard pool-export package (ZIP or directory) into an ItemBank.

	Args:
		infile: Path to a Blackboard pool-export ZIP or an unzipped pool directory.
		allow_mixed: When True, the returned ItemBank accepts mixed item types
			(pool exports are frequently mixed, e.g. MC + MATCH in one pool).

	Returns:
		An ItemBank holding every parsed item from every pool resource in the
		package.
	"""
	# A ZIP needs extracting first; a directory is read in place.
	if zipfile.is_zipfile(infile):
		new_item_bank = _read_from_zip(infile, allow_mixed)
	elif os.path.isdir(infile):
		new_item_bank = _read_from_directory(infile, allow_mixed)
	else:
		raise ValueError(
			f"Input is neither a ZIP file nor a directory: '{infile}'"
		)
	return new_item_bank

#============================================
def _read_from_zip(zip_path: str, allow_mixed: bool) -> item_bank.ItemBank:
	"""
	Extract a pool-export ZIP to a temp directory and read it.

	Args:
		zip_path: Path to the pool-export ZIP.
		allow_mixed: Passed through to the ItemBank.

	Returns:
		The parsed ItemBank.
	"""
	# Extract into a self-cleaning temp directory, then read it as a directory.
	with tempfile.TemporaryDirectory() as temp_dir:
		with zipfile.ZipFile(zip_path, "r") as zip_file:
			zip_file.extractall(temp_dir)
		# Some exports nest the package one folder deep inside the ZIP; resolve
		# to whichever directory actually holds the manifest.
		pool_root = _find_manifest_root(temp_dir)
		new_item_bank = _read_from_directory(pool_root, allow_mixed)
	return new_item_bank

#============================================
def _find_manifest_root(start_dir: str) -> str:
	"""
	Find the directory that holds `imsmanifest.xml` within an extracted tree.

	Args:
		start_dir: The directory to search from.

	Returns:
		The directory path containing the manifest.
	"""
	# Fast path: the manifest sits directly in start_dir.
	if os.path.isfile(os.path.join(start_dir, MANIFEST_FILENAME)):
		return start_dir
	# Otherwise walk until the manifest is found (handles single-folder nesting).
	for current_dir, _subdirs, filenames in os.walk(start_dir):
		if MANIFEST_FILENAME in filenames:
			return current_dir
	raise ValueError(
		f"No {MANIFEST_FILENAME} found in extracted package under '{start_dir}'"
	)

#============================================
def _read_from_directory(pool_dir: str, allow_mixed: bool) -> item_bank.ItemBank:
	"""
	Read an unzipped pool directory into an ItemBank.

	Args:
		pool_dir: A directory containing `imsmanifest.xml` and the pool `.dat`.
		allow_mixed: Passed through to the ItemBank.

	Returns:
		The parsed ItemBank.
	"""
	manifest_path = os.path.join(pool_dir, MANIFEST_FILENAME)
	if not os.path.isfile(manifest_path):
		raise ValueError(
			f"Missing {MANIFEST_FILENAME} in pool directory '{pool_dir}'"
		)
	# Resolve every pool resource the manifest declares (usually one).
	pool_dat_names = _find_pool_dat_filenames(manifest_path)
	if not pool_dat_names:
		raise ValueError(
			f"Manifest '{manifest_path}' declares no '{POOL_RESOURCE_TYPE}' resource"
		)
	new_item_bank = item_bank.ItemBank(allow_mixed)
	# Read every pool resource into one combined bank.
	for pool_dat_name in pool_dat_names:
		pool_dat_path = os.path.join(pool_dir, pool_dat_name)
		if not os.path.isfile(pool_dat_path):
			raise ValueError(
				f"Manifest points to missing pool file '{pool_dat_name}' in '{pool_dir}'"
			)
		_parse_pool_into_bank(pool_dat_path, new_item_bank)
	return new_item_bank

#============================================
def _find_pool_dat_filenames(manifest_path: str) -> list[str]:
	"""
	Read the manifest and return every pool resource's `.dat` filename.

	The pool resource is identified by `type="assessment/x-bb-qti-pool"`; its
	`.dat` filename is the namespaced `bb:file` attribute, not the resource id.

	Args:
		manifest_path: Path to `imsmanifest.xml`.

	Returns:
		The pool `.dat` filenames, in manifest order.
	"""
	tree = lxml.etree.parse(manifest_path)
	root = tree.getroot()
	bb_file_attr = f"{{{BB_NAMESPACE}}}file"
	pool_dat_names = []
	# Scan every <resource>; keep those typed as the BB pool.
	for resource in root.iter("resource"):
		if resource.get("type") != POOL_RESOURCE_TYPE:
			continue
		dat_filename = resource.get(bb_file_attr)
		# A pool resource with no bb:file is malformed; surface it rather than
		# silently dropping the only pool the package carries.
		if not dat_filename:
			raise ValueError(
				f"Pool resource in '{manifest_path}' has no bb:file attribute"
			)
		pool_dat_names.append(dat_filename)
	return pool_dat_names

#============================================
def _parse_pool_into_bank(pool_dat_path: str, new_item_bank: item_bank.ItemBank) -> None:
	"""
	Parse every `<item>` in one pool `.dat` and add the items to the bank.

	Args:
		pool_dat_path: Path to a pool `.dat` (the `assessment/x-bb-qti-pool` XML).
		new_item_bank: The ItemBank to add parsed items to.
	"""
	tree = lxml.etree.parse(pool_dat_path)
	root = tree.getroot()
	dat_filename = os.path.basename(pool_dat_path)
	# Each question is one <item>; iterate them in document order.
	for item_index, item_el in enumerate(root.iter("item")):
		item_cls = _parse_one_item(item_el, dat_filename, item_index)
		# A None result means the item was skipped (unknown type or malformed);
		# the per-item helper already warned with the source name.
		if item_cls is not None:
			new_item_bank.add_item_cls(item_cls)

#============================================
def _parse_one_item(
	item_el: lxml.etree.Element,
	dat_filename: str,
	item_index: int,
) -> item_types.BaseItem | None:
	"""
	Parse a single `<item>` element into an internal item, or skip it.

	Args:
		item_el: The `<item>` lxml element.
		dat_filename: The pool `.dat` filename, used in warning messages.
		item_index: The item's positional index, used in warning messages.

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
		item_cls = read_function(item_el)
	except (ValueError, IndexError, KeyError, AttributeError) as exc:
		print(f"Warning: skipping malformed {source}: {exc}")
		return None
	return item_cls

#============================================
# Shared element-text extraction helpers
#============================================
#============================================
def _smart_text(material_owner: lxml.etree.Element) -> str:
	"""
	Read the HTML payload from the first SMART_TEXT material under an element.

	The write path stores HTML as the `.text` of a
	`mat_formattedtext type="SMART_TEXT"`; lxml escaped it once on write and
	un-escapes it once here, recovering the original HTML verbatim.

	Args:
		material_owner: An element whose subtree contains a
			`mat_formattedtext` element (a flow, response_label, etc.).

	Returns:
		The un-escaped HTML string (empty string when the carrier is empty).
	"""
	# The first SMART_TEXT carrier anywhere beneath this element holds the HTML.
	mat = material_owner.find(".//mat_formattedtext")
	if mat is None:
		raise ValueError("no mat_formattedtext element found")
	# lxml returns the un-escaped text; None text (empty element) reads as "".
	return mat.text if mat.text is not None else ""

#============================================
def _question_html(item_el: lxml.etree.Element) -> str:
	"""
	Read the question HTML from an item's `QUESTION_BLOCK`.

	Args:
		item_el: The `<item>` element.

	Returns:
		The un-escaped question HTML.
	"""
	# The question text lives in the single flow class="QUESTION_BLOCK".
	question_block = _find_flow_by_class(item_el, "QUESTION_BLOCK")
	if question_block is None:
		raise ValueError("no QUESTION_BLOCK flow found")
	return _smart_text(question_block)

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
def _read_choice_labels(response_lid: lxml.etree.Element) -> tuple[list[str], list[str]]:
	"""
	Read the choice idents and choice HTML texts from a choice `response_lid`.

	Args:
		response_lid: The choice `<response_lid>` element.

	Returns:
		A tuple of (label idents, choice HTML strings), index-aligned.
	"""
	label_idents = []
	choice_texts = []
	# Each response_label is one choice; its ident keys scoring, its text is shown.
	for response_label in response_lid.iter("response_label"):
		label_idents.append(response_label.get("ident"))
		choice_texts.append(_smart_text(response_label))
	if not choice_texts:
		raise ValueError("choice question has no response_label choices")
	return label_idents, choice_texts

#============================================
def _correct_choice_idents(item_el: lxml.etree.Element) -> list[str]:
	"""
	Read the correct label idents from the `title="correct"` resprocessing branch.

	The correct branch holds one `<varequal respident="...">LABEL_IDENT</varequal>`
	per correct choice; the varequal TEXT is the correct label ident.

	Args:
		item_el: The `<item>` element.

	Returns:
		The correct label idents, in branch order.
	"""
	resprocessing = _resprocessing(item_el)
	correct_idents = []
	# The correct branch is titled "correct"; its varequal texts name the answers.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") != "correct":
			continue
		for varequal in respcondition.iter("varequal"):
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
def _read_choice_item(item_el: lxml.etree.Element) -> item_types.BaseItem:
	"""
	Read an MC or MA item, choosing the type from the response cardinality.

	`rcardinality="Multiple"` is MA; otherwise MC. This refines the
	`bbmd_questiontype` marker, which Blackboard sometimes labels "Multiple
	Choice" even for multi-select questions.

	Args:
		item_el: The `<item>` element.

	Returns:
		An MC or MA item instance.
	"""
	question_html = _question_html(item_el)
	response_lid = _choice_response_lid(item_el)
	label_idents, choice_texts = _read_choice_labels(response_lid)
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
def _read_FIB(item_el: lxml.etree.Element) -> item_types.FIB:
	"""
	Read a Fill in the Blank item.

	Each accepted answer is the text of a `<varequal respident="response">` in
	its own (UUID-titled) respcondition; the `incorrect` branch is excluded.

	Args:
		item_el: The `<item>` element.

	Returns:
		A FIB item instance.
	"""
	question_html = _question_html(item_el)
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
def _read_MULTI_FIB(item_el: lxml.etree.Element) -> item_types.MULTI_FIB:
	"""
	Read a Fill in the Blank Plus item.

	The `title="correct"` branch holds an `<and>` of one `<or>` per blank; each
	`<or>` carries one `<varequal respident="KEY">` per accepted answer for that
	blank. The answer_map keys are the per-blank `respident` values.

	Args:
		item_el: The `<item>` element.

	Returns:
		A MULTI_FIB item instance.
	"""
	question_html = _question_html(item_el)
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
def _read_NUM(item_el: lxml.etree.Element) -> item_types.NUM:
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

	Returns:
		A NUM item instance.
	"""
	question_html = _question_html(item_el)
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
def _read_MATCH(item_el: lxml.etree.Element) -> item_types.MATCH:
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

	Returns:
		A MATCH item instance with prompts and choices in paired order.
	"""
	question_html = _question_html(item_el)
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
	choice_texts = _read_right_match_texts(right_match_block)

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
		prompt_text = _match_prompt_text(prompt_block)
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
def _read_right_match_texts(right_match_block: lxml.etree.Element) -> list[str]:
	"""
	Read the right-side choice texts from a `RIGHT_MATCH_BLOCK`, in order.

	Args:
		right_match_block: The `<flow class="RIGHT_MATCH_BLOCK">` element.

	Returns:
		The choice HTML strings, in document order.
	"""
	choice_texts = []
	# Each direct child flow class="Block" is one choice's formatted text.
	for choice_flow in right_match_block.findall("flow"):
		choice_texts.append(_smart_text(choice_flow))
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
def _match_prompt_text(prompt_block: lxml.etree.Element) -> str:
	"""
	Read a MATCH prompt's display text from its FORMATTED_TEXT_BLOCK.

	The prompt block holds the response_lid first, then a sibling
	`flow class="FORMATTED_TEXT_BLOCK"` carrying the prompt's own SMART_TEXT.

	Args:
		prompt_block: The per-prompt `<flow class="Block">` element.

	Returns:
		The un-escaped prompt HTML.
	"""
	# The prompt's display text is the FORMATTED_TEXT_BLOCK that is a direct
	# child of the prompt block (not the one nested inside the response_lid).
	for flow in prompt_block.findall("flow"):
		if flow.get("class") == "FORMATTED_TEXT_BLOCK":
			return _smart_text(flow)
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
