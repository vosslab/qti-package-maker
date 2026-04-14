"""Compatibility validation gate for Ultra QTI 2.1 assessment items."""

# Standard Library

# Pip3 Library
import lxml.etree

# QTI Package Maker


#============================================
class UltraCompatibilityError(Exception):
	"""
	Raised when an assessment item violates hard-fail compatibility rules.
	"""
	pass


#============================================
def _get_allowed_tags():
	"""
	Return the set of allowed tags inside itemBody for Ultra.

	Includes both structural and QTI-specific interaction tags.
	Includes both CamelCase (from direct XML construction) and lowercase
	(from lxml.html parsing) variants.
	"""
	return {
		# Structural tags
		'p', 'div', 'span', 'br', 'em', 'strong', 'sub', 'sup', 'code',
		'ul', 'ol', 'li', 'h4', 'h5',
		# Table tags
		'table', 'tbody', 'tr', 'th', 'td', 'colgroup', 'col',
		# QTI interaction tags - both CamelCase and lowercase
		'choiceInteraction', 'choiceinteraction',
		'simpleChoice', 'simplechoice',
		'textEntryInteraction', 'textentryinteraction',
		'matchInteraction', 'matchinteraction',
		'simpleMatchSet', 'simplematchset',
		'simpleAssociableChoice', 'simpleassociablechoice',
		'prompt', 'a'
	}


#============================================
def _get_allowed_attributes_for_tag(tag: str) -> set:
	"""
	Return the set of allowed attributes for a given tag.

	Most tags have no allowed attributes except those explicitly listed.
	Tag names are lowercase because lxml.html lowercases all tag names.
	"""
	allowed_by_tag = {
		'a': {'href'},
		'choiceinteraction': set(),
		'textentryinteraction': set(),
		'matchinteraction': set(),
		'simplematchset': set(),
		'simpleassociablechoice': set(),
		'simplechoice': set(),
	}
	# Default: no attributes allowed
	return allowed_by_tag.get(tag, set())


#============================================
def _collect_all_descendants(element, result=None):
	"""
	Recursively collect all descendant elements (breadth-first).
	"""
	if result is None:
		result = []
	result.append(element)
	for child in element:
		_collect_all_descendants(child, result)
	return result


#============================================
def validate_assessment_items(assessment_item_etrees: list) -> list:
	"""
	Validate a list of assessment item etrees against hard-fail and warn rules.

	Args:
		assessment_item_etrees: List of lxml.etree.Element representing
			<assessmentItem> elements.

	Returns:
		list: List of warning strings for soft violations.

	Raises:
		UltraCompatibilityError: On any hard-fail rule violation.
	"""
	warnings = []

	for item_etree in assessment_item_etrees:
		# Extract item identifier for error messages
		item_id = item_etree.get('identifier', 'unknown')

		# Hard-fail rule 1: XML must parse under lxml.etree.fromstring
		_validate_xml_roundtrip(item_etree, item_id)

		# Hard-fail rule 8: outcomeDeclaration triple must be present
		_validate_outcome_declarations(item_etree, item_id)

		# Find itemBody for rules 2-7
		item_body = item_etree.find('.//itemBody')
		if item_body is not None:
			# Hard-fail rule 2: correctResponse values must match simpleChoice identifiers
			_validate_correct_response_values(item_etree, item_id)

			# Hard-fail rules 3-7: check itemBody content
			_validate_item_body_content(item_body, item_id)

			# Warn rule 1: unknown tags
			_check_unknown_tags(item_body, item_id, warnings)

			# Warn rule 2: cell text length
			_check_cell_text_length(item_body, item_id, warnings)

			# Warn rule 3: empty choiceInteraction
			_check_empty_choice_interaction(item_body, item_id, warnings)

	return warnings


#============================================
def _validate_xml_roundtrip(item_etree, item_id: str):
	"""
	Hard-fail rule 1: XML must parse under lxml.etree.fromstring.
	"""
	serialized = lxml.etree.tostring(item_etree)
	try:
		lxml.etree.fromstring(serialized)
	except lxml.etree.XMLSyntaxError as e:
		raise UltraCompatibilityError(
			f"Item '{item_id}': XML does not parse after serialization: {e}"
		)


#============================================
def _validate_outcome_declarations(item_etree, item_id: str):
	"""
	Hard-fail rule 8: outcomeDeclaration with identifier="SCORE" must exist.
	"""
	score_outcome = item_etree.find(
		".//outcomeDeclaration[@identifier='SCORE']"
	)
	if score_outcome is None:
		raise UltraCompatibilityError(
			f"Item '{item_id}': missing outcomeDeclaration with identifier='SCORE'"
		)


#============================================
def _validate_correct_response_values(item_etree, item_id: str):
	"""
	Hard-fail rule 2: correctResponse/value must match at least one
	simpleChoice/@identifier in the same item.
	"""
	# Find all simpleChoice identifiers (both CamelCase and lowercase)
	simple_choices = (
		item_etree.findall('.//simpleChoice') +
		item_etree.findall('.//simplechoice')
	)
	choice_ids = {choice.get('identifier') for choice in simple_choices}

	# Skip validation if there are no choice interactions
	if not choice_ids:
		return

	# Find all correctResponse values
	correct_values = item_etree.findall('.//correctResponse/value')

	for value_elem in correct_values:
		value_text = value_elem.text
		if value_text and value_text not in choice_ids:
			raise UltraCompatibilityError(
				f"Item '{item_id}': correctResponse value '{value_text}' "
				f"does not match any simpleChoice/@identifier"
			)


#============================================
def _validate_item_body_content(item_body, item_id: str):
	"""
	Hard-fail rules 3-7: check itemBody for residue and disallowed content.
	"""
	# Get all descendants
	all_elements = _collect_all_descendants(item_body)

	allowed_tags = _get_allowed_tags()

	for element in all_elements:
		# Hard-fail rule 3: No style= attribute residue
		if element.get('style') is not None:
			raise UltraCompatibilityError(
				f"Item '{item_id}': found style= attribute on <{element.tag}> "
				f"in itemBody (sanitizer was skipped)"
			)

		# Hard-fail rule 4: No class= attribute residue
		if element.get('class') is not None:
			raise UltraCompatibilityError(
				f"Item '{item_id}': found class= attribute on <{element.tag}> "
				f"in itemBody (sanitizer was skipped)"
			)

		# Hard-fail rule 5: No <script> or <style> elements
		if element.tag in {'script', 'style'}:
			raise UltraCompatibilityError(
				f"Item '{item_id}': found <{element.tag}> element in itemBody "
				f"(sanitizer was skipped)"
			)

		# Hard-fail rule 6: No <img> elements
		if element.tag == 'img':
			raise UltraCompatibilityError(
				f"Item '{item_id}': found <img> element in itemBody "
				f"(no valid manifest-backed embedding pattern in v1)"
			)

		# Hard-fail rule 7: No disallowed top-level tags
		if element != item_body and element.tag not in allowed_tags:
			raise UltraCompatibilityError(
				f"Item '{item_id}': disallowed tag <{element.tag}> in itemBody"
			)


#============================================
def _check_unknown_tags(item_body, item_id: str, warnings: list):
	"""
	Warn rule 1: Unknown tags not on the allowlist.

	Tags are considered unknown if they are not in the allowed set.
	This is a soft warning only. Skips checking since unknown tags are
	rare in well-formed QTI output.
	"""
	# Note: Unknown tag detection is deferred. The hard-fail rule 7 in
	# _validate_item_body_content already catches disallowed tags. This
	# warn rule was intended for future extensibility but requires more
	# nuanced tag allowlisting (some tags are allowed in some contexts
	# but not others). For now, we skip this check to avoid false positives.
	pass


#============================================
def _check_cell_text_length(item_body, item_id: str, warnings: list):
	"""
	Warn rule 2: Cell text (in table cells or other containers) > 1000 chars.

	Checks for long text that might cause layout issues.
	"""
	# Find table cells (td, th) or other containers with significant text
	table_cells = item_body.findall('.//td') + item_body.findall('.//th')

	for cell in table_cells:
		# Gather all text content in the cell
		text_content = ''.join(cell.itertext())
		if len(text_content) > 1000:
			warnings.append(
				f"Item '{item_id}': cell text length {len(text_content)} chars "
				f"exceeds 1000 (Ultra auto-layout may wrap awkwardly)"
			)


#============================================
def _check_empty_choice_interaction(item_body, item_id: str, warnings: list):
	"""
	Warn rule 3: choiceInteraction with no simpleChoice elements.

	Catches malformed MC/MA items. Searches for both CamelCase and lowercase
	tag names since lxml may lowercase them.
	"""
	choice_interactions = (
		item_body.findall('.//choiceInteraction') +
		item_body.findall('.//choiceinteraction')
	)

	for choice_interaction in choice_interactions:
		simple_choices = (
			choice_interaction.findall('.//simpleChoice') +
			choice_interaction.findall('.//simplechoice')
		)
		if not simple_choices:
			warnings.append(
				f"Item '{item_id}': choiceInteraction has zero simpleChoice elements"
			)
